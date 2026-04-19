import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from collection_compiler_service.repository.CaseAssignmentDetailRepository import CaseAssignmentDetailRepository
from collection_compiler_service.services.file_ocr_service import file_ocr_service
from collection_compiler_service.services.file_search_service import file_search_service
from collection_compiler_service.services.ai_info_extraction_service import ai_info_extraction_service

logger = logging.getLogger("collection_compiler_service")

# 全局进程池，最多1个worker避免CPU过载
_process_pool = ProcessPoolExecutor(max_workers=1)


def _ocr_batch_sync(batch: list[str]) -> dict[str, list[dict]]:
    """同步执行 OCR（在独立进程中运行）"""
    import asyncio
    from collection_compiler_service.services.file_ocr_service import file_ocr_service
    return asyncio.run(file_ocr_service.ocr_files(batch))


class FileOcrProcessService:

    async def _extract_and_log_info(self, case_result: dict[str, Any]) -> None:
        """异步提取 AI 信息并保存到数据库"""
        try:
            extracted_info = await ai_info_extraction_service.extract_info_from_case(case_result)
            logger.info(f"case_id={case_result.get('case_id')} AI 提取信息: {extracted_info}")

            # 保存到数据库
            case_id = case_result.get('case_id')
            if case_id and any(extracted_info.values()):
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    from sqlalchemy import select
                    from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M

                    stmt = select(M).where(M.id == case_id)
                    result = await repo.db.execute(stmt)
                    case = result.scalar_one_or_none()

                    if case:
                        if extracted_info.get('name'):
                            case.debtor_name = extracted_info['name']
                        if extracted_info.get('household_address'):
                            case.household_address = extracted_info['household_address']
                        if extracted_info.get('province'):
                            case.province = extracted_info['province']
                        if extracted_info.get('city'):
                            case.city = extracted_info['city']

                        await repo.update_by_id(case)
                        logger.info(f"case_id={case_id} AI 提取信息已保存到数据库")
                    else:
                        logger.warning(f"case_id={case_id} 未找到对应案件记录")
        except Exception as e:
            logger.error(f"case_id={case_result.get('case_id')} AI 提取失败: {e}")

    async def process_by_file_hash(self, file_hash: str) -> dict[str, Any]:
        """
        查询 file_hash 对应的待处理案件（case_status=0），
        找到关联文件路径，批量 OCR 识别后返回结果。
        """
        async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
            from sqlalchemy import select, and_
            from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
            stmt = select(M).where(and_(M.del_flag == 0, M.file_hash == file_hash, M.case_status <= 0))
            result = await repo.db.execute(stmt)
            pending = list(result.scalars().all())

        if not pending:
            return {"file_hash": file_hash, "pending_count": 0, "ocr_results": []}

        # all_results = []
        # for case in pending[28:29]:
        for case in pending:
            file_paths: list[str] = []
            found = file_search_service.find_files(case.application_code, case.uid)
            for paths in found.values():
                file_paths.extend(p for p in paths if not p.lower().endswith(".pdf"))

            # 如果没有找到文件，设置状态为 4（缺少处理数据）并跳过
            if not file_paths:
                logger.warning(f"case_id={case.id} 未找到可处理文件，设置状态为 4")
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    from sqlalchemy import update
                    from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
                    stmt = update(M).where(M.id == case.id).values(case_status=4)
                    await repo.db.execute(stmt)
                    await repo.db.commit()
                continue

            case_result = {
                "case_id": case.id,
                "application_code": case.application_code,
                "uid": case.uid,
                "files": []
            }


            try:
                # 开始处理，更新状态为处理中
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    from sqlalchemy import update
                    from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
                    stmt = update(M).where(M.id == case.id).values(case_status=1)
                    await repo.db.execute(stmt)
                    await repo.db.commit()
                logger.info(f"case_id={case.id} OCR 处理中，状态更新为 1")

                # 每次只处理5张图片,避免cpu满载导致程序其他接口被阻塞
                for i in range(0, len(file_paths), 5):
                    batch = file_paths[i:i + 5]
                    logger.info(f"处理 case_id={case.id} 第 {i // 5 + 1} 批，共 {len(batch)} 张")
                    # 在独立进程中执行 OCR，完全隔离 CPU 占用
                    loop = asyncio.get_event_loop()
                    ocr_results = await loop.run_in_executor(_process_pool, _ocr_batch_sync, batch)

                    for path, items in ocr_results.items():
                        text = file_ocr_service.extract_text(items)
                        case_result["files"].append({
                            "file_path": path,
                            "ocr_text": text
                        })

                # 异步调用 AI 提取信息（fire-and-forget）
                asyncio.create_task(self._extract_and_log_info(case_result))

                print(case_result)

                # OCR 成功，更新状态为已完成
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    from sqlalchemy import update
                    from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
                    stmt = update(M).where(M.id == case.id).values(case_status=2)
                    await repo.db.execute(stmt)
                    await repo.db.commit()
                logger.info(f"case_id={case.id} OCR 完成，状态更新为 2")

            except Exception as e:
                # OCR 失败，更新状态为失败
                logger.error(f"case_id={case.id} OCR 失败: {e}")
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    from sqlalchemy import update
                    from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
                    stmt = update(M).where(M.id == case.id).values(case_status=3)
                    await repo.db.execute(stmt)
                    await repo.db.commit()



            # all_results.append(case_result)


file_ocr_process_service = FileOcrProcessService()