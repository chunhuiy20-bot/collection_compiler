"""
文件名: OcrService.py
作者: yangchunhui
创建日期: 2026/4/19
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/19
描述: OCR 服务统一入口，基于注册表模式管理多个 OCR 引擎。支持运行时注册、切换引擎，同时提供同步和异步两种调用方式。引擎在注册时初始化为单例，切换引擎只需修改当前引擎名称，不重新加载模型。

修改历史:
2026/4/19 - yangchunhui - 初始版本

依赖:
- common.utils.ocr.BaseOcrEngine: OCR 引擎抽象基类

使用示例:
"""
from common.utils.ocr.BaseOcrEngine import BaseOcrEngine


class OcrService:
    _engines: dict[str, BaseOcrEngine] = {}
    _current: str = "paddle"

    @classmethod
    def register(cls, name: str, engine: BaseOcrEngine) -> None:
        cls._engines[name] = engine

    @classmethod
    def use(cls, name: str) -> None:
        if name not in cls._engines:
            raise ValueError(f"OCR 引擎 '{name}' 未注册，可用: {list(cls._engines.keys())}")
        cls._current = name

    @classmethod
    def ocr_file_sync(cls, image_path: str) -> list[dict]:
        return cls._engines[cls._current].ocr_file_sync(image_path)

    @classmethod
    def ocr_bytes_sync(cls, image_bytes: bytes) -> list[dict]:
        return cls._engines[cls._current].ocr_bytes_sync(image_bytes)

    @classmethod
    async def ocr_file(cls, image_path: str) -> list[dict]:
        return await cls._engines[cls._current].ocr_file(image_path)

    @classmethod
    async def ocr_bytes(cls, image_bytes: bytes) -> list[dict]:
        return await cls._engines[cls._current].ocr_bytes(image_bytes)

    @classmethod
    def current(cls) -> str:
        return cls._current

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._engines.keys())
