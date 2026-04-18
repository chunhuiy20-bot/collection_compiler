"""
文件名: BaseOcrEngine.py
作者: yangchunhui
创建日期: 2026/4/19
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/19
描述: OCR 引擎抽象基类，定义统一的 OCR 识别接口。子类需实现同步方法 ocr_file_sync 和 ocr_bytes_sync，基类自动提供基于 run_in_executor 的异步包装方法 ocr_file 和 ocr_bytes，支持在 FastAPI 等异步框架中非阻塞调用。

修改历史:
2026/4/19 - yangchunhui - 初始版本

依赖:
- abc: 提供抽象基类支持（ABC, abstractmethod）
- asyncio: 提供事件循环和线程池执行器支持

使用示例:
"""
from abc import ABC, abstractmethod


class BaseOcrEngine(ABC):

    @abstractmethod
    def ocr_file_sync(self, image_path: str) -> list[dict]:
        """同步识别图片文件"""

    @abstractmethod
    def ocr_bytes_sync(self, image_bytes: bytes) -> list[dict]:
        """同步识别图片字节流"""

    async def ocr_file(self, image_path: str) -> list[dict]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.ocr_file_sync, image_path)

    async def ocr_bytes(self, image_bytes: bytes) -> list[dict]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.ocr_bytes_sync, image_bytes)
