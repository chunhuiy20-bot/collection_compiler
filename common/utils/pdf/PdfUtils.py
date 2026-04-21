"""
文件名: PdfUtils.py
作者: yangchunhui
创建日期: 2026/4/21
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/4/21
描述: PDF 工具类，提供将 PDF 按页转换为 JPG 图片的方法。

依赖:
- pymupdf (fitz): pip install pymupdf
"""
import os
import fitz


class PdfUtils:

    @staticmethod
    def pdf_to_jpg(pdf_path: str, save_dir: str = None, dpi: int = 150) -> list[str]:
        """
        将 PDF 每页转换为 JPG 图片。

        :param pdf_path: PDF 文件的绝对路径
        :param save_dir: 图片保存目录（绝对路径），为空则保存到 pdf_path 同级目录
        :param dpi: 渲染分辨率，默认 150
        :return: 生成的图片绝对路径列表
        """
        if save_dir is None:
            save_dir = os.path.dirname(pdf_path)

        os.makedirs(save_dir, exist_ok=True)

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        result = []

        doc = fitz.open(pdf_path)
        try:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            for i, page in enumerate(doc):
                img_path = os.path.join(save_dir, f"{pdf_name}_page_{i + 1}.jpg")
                page.get_pixmap(matrix=mat).save(img_path)
                result.append(img_path)
        finally:
            doc.close()

        return result

    @staticmethod
    def pdf_to_single_jpg(pdf_path: str, save_dir: str = None, dpi: int = 150) -> str:
        """
        将 PDF 所有页纵向拼接为一张 JPG 图片。

        :param pdf_path: PDF 文件的绝对路径
        :param save_dir: 图片保存目录（绝对路径），为空则保存到 pdf_path 同级目录
        :param dpi: 渲染分辨率，默认 150
        :return: 生成的图片绝对路径
        """
        if save_dir is None:
            save_dir = os.path.dirname(pdf_path)

        os.makedirs(save_dir, exist_ok=True)

        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        doc = fitz.open(pdf_path)
        try:
            pixmaps = [page.get_pixmap(matrix=mat) for page in doc]
        finally:
            doc.close()

        from PIL import Image
        import io

        images = [Image.open(io.BytesIO(p.tobytes("png"))) for p in pixmaps]
        width = images[0].width
        total_height = sum(img.height for img in images)

        merged = Image.new("RGB", (width, total_height), (255, 255, 255))
        y = 0
        for img in images:
            merged.paste(img, (0, y))
            y += img.height

        img_path = os.path.join(save_dir, f"{pdf_name}_merged.jpg")
        merged.save(img_path, "JPEG")
        return img_path
