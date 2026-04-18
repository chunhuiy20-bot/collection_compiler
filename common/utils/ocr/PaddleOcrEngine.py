"""
文件名: PaddleOcrEngine.py
作者: yangchunhui
创建日期: 2026/4/19
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/19
描述: 基于 PaddleOCR 的 OCR 引擎实现。继承 BaseOcrEngine，实现同步识别方法，支持图片文件路径和字节流两种输入方式。PaddleOCR 实例在初始化时单例化，避免重复加载模型。识别结果统一返回 [{"text": ..., "score": ..., "box": ...}] 格式。

修改历史:
2026/4/19 - yangchunhui - 初始版本

依赖:
- paddleocr: PaddleOCR 识别引擎
- tempfile: 用于字节流识别时创建临时文件
- os: 临时文件清理
- common.utils.ocr.BaseOcrEngine: OCR 引擎抽象基类

使用示例:
"""
import os
import tempfile

from common.utils.ocr.BaseOcrEngine import BaseOcrEngine


class PaddleOcrEngine(BaseOcrEngine):

    def __init__(self, lang: str = "ch"):
        import paddle
        from paddleocr import PaddleOCR
        use_gpu = paddle.device.cuda.device_count() > 0
        self._ocr = PaddleOCR(use_textline_orientation=True, lang=lang, use_gpu=use_gpu)

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
        for res in results:
            for text, score, box in zip(res["rec_texts"], res["rec_scores"], res["rec_polys"]):
                output.append({"text": text, "score": score, "box": box.tolist()})
        return output
