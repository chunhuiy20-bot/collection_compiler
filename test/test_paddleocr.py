"""
PaddleOCR 测试 Demo
使用前请先安装依赖：
    pip install paddlepaddle paddleocr
"""

from paddleocr import PaddleOCR
import os
import sys


def ocr_image(image_path: str):
    """对单张图片进行 OCR 识别"""
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}")
        return

    # 初始化 OCR，use_angle_cls 开启方向分类，lang 设置语言
    ocr = PaddleOCR(use_angle_cls=True, lang="ch")

    # 执行识别
    results = ocr.ocr(image_path)

    for res in results:
        for text, score, box in zip(res["rec_texts"], res["rec_scores"], res["rec_polys"]):
            print(f"文字: {text}  置信度: {score:.4f}")
            print(f"  坐标: {box.tolist()}")
            print()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        ocr_image(sys.argv[1])
    else:
        test_dir = os.path.dirname(__file__)
        images = [f for f in os.listdir(test_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if not images:
            print("test 目录下没有图片")
            sys.exit(1)
        for img in images:
            path = os.path.join(test_dir, img)
            print(f"\n=== {img} ===")
            ocr_image(path)
