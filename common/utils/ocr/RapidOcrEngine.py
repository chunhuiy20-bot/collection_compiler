"""
文件名: RapidOcrEngine.py
作者: yangchunhui
创建日期: 2026/4/19
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/19
描述: 基于 RapidOCR + ONNX Runtime 的 OCR 引擎实现，适合 Apple Silicon (M 系列) 部署。
     在 macOS 上 ONNX Runtime 会自动启用 CoreML 执行提供程序，充分利用 Neural Engine。
     识别结果统一返回 [{"text": ..., "score": ..., "box": ...}] 格式。

修改历史:
2026/4/19 - yangchunhui - 初始版本

依赖:
- rapidocr-onnxruntime: pip install rapidocr-onnxruntime
- Apple Silicon CoreML 加速: pip install onnxruntime-silicon (macOS only)
"""
import os
import platform
import tempfile
from rapidocr_onnxruntime import RapidOCR
from common.utils.ocr.BaseOcrEngine import BaseOcrEngine

class RapidOcrEngine(BaseOcrEngine):

    def __init__(self, use_gpu: bool | None = None):
        providers = self._resolve_providers(use_gpu)
        print(f"[RapidOCR] 使用: {providers[0] if providers else 'CPUExecutionProvider'}")
        if providers:
            self._ocr = RapidOCR(providers=providers)
        else:
            self._ocr = RapidOCR()

    @staticmethod
    def _resolve_providers(use_gpu: bool | None) -> list[str] | None:
        # Apple Silicon: 优先 CoreML，回退 CPU
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return ["CoreMLExecutionProvider", "CPUExecutionProvider"]

        # Windows/Linux: 可选 CUDA EP
        if use_gpu is None:
            try:
                import onnxruntime as ort
                use_gpu = "CUDAExecutionProvider" in ort.get_available_providers()
            except Exception:
                use_gpu = False

        if use_gpu:
            try:
                import onnxruntime as ort
                if "CUDAExecutionProvider" in ort.get_available_providers():
                    return ["CUDAExecutionProvider", "CPUExecutionProvider"]
                print("[RapidOCR] 未检测到 CUDA EP，自动降级到 CPU")
            except Exception:
                pass

        return None

    def ocr_file_sync(self, image_path: str) -> list[dict]:
        result, _ = self._ocr(image_path)
        return self._parse(result)

    def ocr_bytes_sync(self, image_bytes: bytes) -> list[dict]:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        try:
            return self.ocr_file_sync(tmp_path)
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _parse(result) -> list[dict]:
        if not result:
            return []
        output = []
        for item in result:
            box, text, score = item[0], item[1], item[2]
            output.append({"text": text, "score": float(score), "box": box})
        return output