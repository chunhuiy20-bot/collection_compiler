import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from sqlalchemy import and_, select, update

from collection_compiler_service.model.CaseAssignmentDetail import CaseAssignmentDetail as M
from collection_compiler_service.repository.CaseAssignmentDetailRepository import CaseAssignmentDetailRepository
from collection_compiler_service.services.ai_info_extraction_service import ai_info_extraction_service
from collection_compiler_service.services.file_ocr_service import file_ocr_service
from collection_compiler_service.services.file_search_service import file_search_service
from collection_compiler_service.services.multimodal_service import multimodal_service

logger = logging.getLogger("collection_compiler_service")

_process_pool = ProcessPoolExecutor(max_workers=1)
_background_tasks: set = set()


def _ocr_batch_sync(batch: list[str]) -> dict[str, list[dict]]:
    import asyncio
    from collection_compiler_service.services.file_ocr_service import file_ocr_service
    return asyncio.run(file_ocr_service.ocr_files(batch))


async def _update_status(case_id: int, status: int) -> None:
    async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
        await repo.db.execute(update(M).where(M.id == case_id).values(case_status=status))
        await repo.db.commit()


class FileOcrProcessService:

    async def _extract_and_log_info(self, case_result: dict[str, Any]) -> None:
        try:
            extracted_info = await ai_info_extraction_service.extract_info_from_case(case_result)
            logger.info(f"case_id={case_result.get('case_id')} AI 提取信息: {extracted_info}")

            case_id = case_result.get('case_id')
            if case_id and any(extracted_info.values()):
                async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
                    result = await repo.db.execute(select(M).where(M.id == case_id))
                    case = result.scalar_one_or_none()
                    if case:
                        for field, attr in [('name', 'debtor_name'), ('household_address', 'household_address'),
                                            ('province', 'province'), ('city', 'city')]:
                            if extracted_info.get(field):
                                setattr(case, attr, extracted_info[field])
                        await repo.update_by_id(case)
                        logger.info(f"case_id={case_id} AI 提取信息已保存到数据库")
                    else:
                        logger.warning(f"case_id={case_id} 未找到对应案件记录")
        except Exception as e:
            logger.error(f"case_id={case_result.get('case_id')} AI 提取失败: {e}")

    async def _ocr_processor(self, case_id: int, file_paths: list[str]) -> list[dict]:
        files = []
        for i in range(0, len(file_paths), 5):
            batch = file_paths[i:i + 5]
            logger.info(f"处理 case_id={case_id} 第 {i // 5 + 1} 批，共 {len(batch)} 张")
            loop = asyncio.get_event_loop()
            ocr_results = await loop.run_in_executor(_process_pool, _ocr_batch_sync, batch)
            for path, items in ocr_results.items():
                files.append({"file_path": path, "ocr_text": file_ocr_service.extract_text(items)})
        return files

    async def _multimodal_processor(self, case_id: int, file_paths: list[str]) -> list[dict]:
        raw = await multimodal_service.extract_id_card_info(file_paths)
        logger.info(f"case_id={case_id} 多模态提取信息: {raw}")
        return [{"file_path": path, "ocr_text": content} for path, content in raw.items()]

    async def _process_cases(self, processor: Callable, file_hash: str = None, uids: list[str] = None) -> dict[str, Any]:
        async with CaseAssignmentDetailRepository(db_name="collection_compiler") as repo:
            if uids:
                condition = and_(M.del_flag == 0, M.uid.in_(uids), M.case_status <= 0)
            else:
                condition = and_(M.del_flag == 0, M.file_hash == file_hash, M.case_status <= 0)
            result = await repo.db.execute(select(M).where(condition))
            pending = list(result.scalars().all())

        if not pending:
            return {"uids": uids, "file_hash": file_hash, "pending_count": 0}

        for case in pending:
            file_paths: list[str] = []
            found = file_search_service.find_files(case.application_code, case.uid)
            for paths in found.values():
                file_paths.extend(p for p in paths if not p.lower().endswith(".pdf"))

            if not file_paths:
                logger.warning(f"case_id={case.id} 未找到可处理文件，设置状态为 4")
                await _update_status(case.id, 4)
                continue

            try:
                await _update_status(case.id, 1)
                logger.info(f"case_id={case.id} 处理中，状态更新为 1")

                files = await processor(case.id, file_paths)
                case_result = {
                    "case_id": case.id,
                    "application_code": case.application_code,
                    "uid": case.uid,
                    "files": files,
                }

                task = asyncio.create_task(self._extract_and_log_info(case_result))
                _background_tasks.add(task)
                task.add_done_callback(_background_tasks.discard)

                await _update_status(case.id, 2)
                logger.info(f"case_id={case.id} 处理完成，状态更新为 2")
            except Exception as e:
                logger.error(f"case_id={case.id} 处理失败: {e}")
                await _update_status(case.id, 3)

        return {"file_hash": file_hash, "uids": uids, "pending_count": len(pending)}

    async def process_by_file_hash(self, file_hash: str) -> dict[str, Any]:
        return await self._process_cases(self._ocr_processor, file_hash=file_hash)

    async def process_by_file_hash_multimodal(self, file_hash: str) -> dict[str, Any]:
        return await self._process_cases(self._multimodal_processor, file_hash=file_hash)

    async def process_by_uids(self, uids: list[str]) -> dict[str, Any]:
        return await self._process_cases(self._ocr_processor, uids=uids)

    async def process_by_uids_multimodal(self, uids: list[str]) -> dict[str, Any]:
        return await self._process_cases(self._multimodal_processor, uids=uids)


file_ocr_process_service = FileOcrProcessService()