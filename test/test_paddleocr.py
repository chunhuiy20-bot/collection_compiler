"""
EasyOCR 测试 Demo
使用前请先安装依赖：
    pip install easyocr
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils.ocr.OcrService import OcrService
from common.utils.ocr.EasyOcrEngine import EasyOcrEngine
from common.utils.ocr.PaddleOcrEngine import PaddleOcrEngine
from common.utils.ocr.CnOcrEngine import CnOcrEngine

async def ocr_image(image_path: str):
    """对单张图片进行 OCR 识别"""
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}")
        return None, image_path

    results = await OcrService.ocr_file(image_path)
    return results, image_path


async def main():

    OcrService.register("paddle",PaddleOcrEngine(use_gpu=False))
    OcrService.use("paddle")

    # OcrService.register("easy", EasyOcrEngine(use_gpu=True))
    # OcrService.use("easy")

    # OcrService.register("cnocr",CnOcrEngine(use_gpu=True))
    # OcrService.use("cnocr")
    if len(sys.argv) >= 2:
        results, _ = await ocr_image(sys.argv[1])
        for item in results:
            print(f"文字: {item['text']}  置信度: {item['score']:.4f}")
            print(f"  坐标: {item['box']}")
            print()
    else:
        test_dir = os.path.dirname(__file__)
        images = [f for f in os.listdir(test_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not images:
            print("test 目录下没有图片")
            sys.exit(1)

        tasks = [ocr_image(os.path.join(test_dir, img)) for img in images]
        all_results = await asyncio.gather(*tasks)

        for results, path in all_results:
            print(f"\n=== {os.path.basename(path)} ===")
            if results:
                for item in results:
                    print(item['text'])
                    # print(f"文字: {item['text']}  置信度: {item['score']:.4f}")
                    # print(f"  坐标: {item['box']}")
                    print()


if __name__ == "__main__":
    asyncio.run(main())