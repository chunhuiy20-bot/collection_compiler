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
import sys
import types
import tempfile

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"

# modelscope 在导入时会 import torch，而 torch cu128 在 Windows 上与 paddlepaddle 的
# cuDNN 版本冲突导致 DLL 加载失败。这里 mock 掉 modelscope.utils.torch_utils，
# 使其不触发 torch 导入，paddle CPU 模式不需要 torch。
if "modelscope.utils.torch_utils" not in sys.modules:
    _mock = types.ModuleType("modelscope.utils.torch_utils")
    _mock.is_dist = lambda: False
    _mock.is_master = lambda: True
    sys.modules["modelscope.utils.torch_utils"] = _mock

from common.utils.ocr.BaseOcrEngine import BaseOcrEngine


class PaddleOcrEngine(BaseOcrEngine):

    def __init__(self, lang: str = "ch", use_gpu: bool | None = None):
        import paddle
        from paddleocr import _common_args
        from paddleocr import PaddleOCR

        cuda_count = paddle.device.cuda.device_count()
        gpu_available = cuda_count > 0

        if use_gpu is None:
            use_gpu = gpu_available
        elif use_gpu and not gpu_available:
            print("[PaddleOCR] 未检测到 GPU，自动降级到 CPU")
            use_gpu = False

        # RTX 5070 (Blackwell CC 12.0) 与当前 PaddlePaddle GPU 推理不兼容，暂强制 CPU
        if use_gpu:
            print("[PaddleOCR] 警告: Blackwell GPU 暂不兼容，降级到 CPU")
            use_gpu = False

        device = "gpu:0" if use_gpu else "cpu"
        print(f"[PaddleOCR] 使用: {'GPU' if use_gpu else 'CPU'}")

        _orig = _common_args.prepare_common_init_args

        def _patched(model_name, common_args):
            result = _orig(model_name, common_args)
            if "pp_option" in result:
                result["pp_option"].enable_new_ir = False
            return result

        _common_args.prepare_common_init_args = _patched
        try:
            self._ocr = PaddleOCR(use_textline_orientation=True, lang=lang, device=device, use_doc_unwarping=False)
        finally:
            _common_args.prepare_common_init_args = _orig

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
