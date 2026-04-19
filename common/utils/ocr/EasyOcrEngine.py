"""
文件名: EasyOcrEngine.py
作者: yangchunhui
创建日期: 2026/4/19
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/19
描述: 基于 EasyOCR 的 OCR 引擎实现，支持 NVIDIA GPU（含 Blackwell 架构）。
     自动检测 CUDA 可用性，有 GPU 则启用，否则降级到 CPU。
     识别结果统一返回 [{"text": ..., "score": ..., "box": ...}] 格式。

修改历史:
2026/4/19 - yangchunhui - 初始版本

依赖:
- easyocr: pip install easyocr
"""
import os
import tempfile

from common.utils.ocr.BaseOcrEngine import BaseOcrEngine


class EasyOcrEngine(BaseOcrEngine):

    def __init__(self, langs: list[str] = None, use_gpu: bool | None = None):
        import torch
        import easyocr

        if langs is None:
            langs = ["ch_sim", "en"]

        if use_gpu is None:
            use_gpu = torch.cuda.is_available()
        elif use_gpu and not torch.cuda.is_available():
            print("[EasyOCR] 未检测到 GPU，自动降级到 CPU")
            use_gpu = False

        print(f"[EasyOCR] 使用: {'GPU' if use_gpu else 'CPU'}")
        self._reader = easyocr.Reader(langs, gpu=use_gpu)

    def ocr_file_sync(self, image_path: str) -> list[dict]:
        import numpy as np
        from PIL import Image
        img = np.array(Image.open(image_path).convert("RGB"))
        results = self._reader.readtext(img)
        return self._parse(results)

    def ocr_bytes_sync(self, image_bytes: bytes) -> list[dict]:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        try:
            return self.ocr_file_sync(tmp_path)
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _parse(results) -> list[dict]:
        output = []
        for box, text, score in results:
            output.append({"text": text, "score": float(score), "box": box})
        return output