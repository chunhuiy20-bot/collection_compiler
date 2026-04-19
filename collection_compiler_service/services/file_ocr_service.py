import asyncio
import logging
from pathlib import Path

from common.utils.ocr.OcrService import OcrService
from common.utils.ocr.PaddleOcrEngine import PaddleOcrEngine

logger = logging.getLogger("collection_compiler_service")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def _init_ocr():
    engine = PaddleOcrEngine(use_gpu=False)
    OcrService.register("paddle", engine)
    OcrService.use("paddle")
    logger.info("OCR 引擎已初始化: %s", OcrService.current())


class FileOcrService:

    def __init__(self):
        if not OcrService.available():
            _init_ocr()

    async def ocr_file(self, file_path: str) -> list[dict]:
        """对单个图片文件进行 OCR，返回识别结果列表"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {path.suffix}")

        logger.info("OCR 识别: %s", file_path)
        results = await OcrService.ocr_file(file_path)
        logger.info("OCR 完成: %s, 识别 %d 条文字", path.name, len(results))
        return results

    async def ocr_bytes(self, image_bytes: bytes, filename: str = "") -> list[dict]:
        """对图片字节流进行 OCR"""
        logger.info("OCR 识别字节流: %s", filename)
        results = await OcrService.ocr_bytes(image_bytes)
        logger.info("OCR 完成: %s, 识别 %d 条文字", filename, len(results))
        return results

    async def ocr_directory(self, dir_path: str) -> dict[str, list[dict]]:
        """对目录下所有支持的图片并发 OCR，返回 {文件名: 识别结果} 字典"""
        directory = Path(dir_path)
        if not directory.is_dir():
            raise FileNotFoundError(f"目录不存在: {dir_path}")

        images = [f for f in directory.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
        if not images:
            return {}

        logger.info("批量 OCR: %s, 共 %d 张图片", dir_path, len(images))

        async def _ocr_one(f: Path):
            try:
                return f.name, await OcrService.ocr_file(str(f))
            except Exception as e:
                logger.warning("OCR 失败: %s, 原因: %s", f.name, e)
                return f.name, []

        results = await asyncio.gather(*[_ocr_one(img) for img in images])
        return dict(results)

    async def ocr_files(self, file_paths: list[str]) -> dict[str, list[dict]]:
        """对文件路径列表并发 OCR，返回 {文件路径: 识别结果} 字典"""
        async def _ocr_one(path: str):
            try:
                return path, await self.ocr_file(path)
            except Exception as e:
                logger.warning("OCR 失败: %s, 原因: %s", path, e)
                return path, []

        results = await asyncio.gather(*[_ocr_one(p) for p in file_paths])
        return dict(results)

    def extract_text(self, ocr_results: list[dict]) -> str:
        """将 OCR 结果列表拼接为纯文本"""
        return "\n".join(item["text"] for item in ocr_results if item.get("text"))


file_ocr_service = FileOcrService()