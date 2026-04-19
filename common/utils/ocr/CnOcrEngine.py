import os
import tempfile

from common.utils.ocr.BaseOcrEngine import BaseOcrEngine


class CnOcrEngine(BaseOcrEngine):

    def __init__(self, use_gpu: bool | None = None):
        import torch
        from cnocr import CnOcr

        if use_gpu is None:
            use_gpu = torch.cuda.is_available()
        elif use_gpu and not torch.cuda.is_available():
            print("[CnOCR] 未检测到 GPU，自动降级到 CPU")
            use_gpu = False

        context = "gpu" if use_gpu else "cpu"
        print(f"[CnOCR] 使用: {'GPU' if use_gpu else 'CPU'}")
        # db_resnet18 使用 PyTorch 检测器，避免与 rapidocr-onnxruntime 的版本冲突
        self._ocr = CnOcr(det_model_name="db_resnet18", context=context)

    def ocr_file_sync(self, image_path: str) -> list[dict]:
        results = self._ocr.ocr(image_path)
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
        for item in results:
            text = item.get("text", "")
            score = float(item.get("score", 0.0))
            box = item.get("position", [])
            if hasattr(box, "tolist"):
                box = box.tolist()
            output.append({"text": text, "score": score, "box": box})
        return output