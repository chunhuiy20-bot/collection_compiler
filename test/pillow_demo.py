from PIL import Image, ImageEnhance
import os

def adjust_brightness_contrast(
    input_abs_path: str,
    output_abs_path: str | None = None,
    brightness: float = 1.0,  # 1.0不变；>1变亮；<1变暗
    contrast: float = 1.0     # 1.0不变；>1对比更强；<1更平
) -> str:
    if not os.path.isabs(input_abs_path):
        raise ValueError("input_abs_path 必须是绝对路径")
    if output_abs_path is not None and not os.path.isabs(output_abs_path):
        raise ValueError("output_abs_path 必须是绝对路径")

    img = Image.open(input_abs_path).convert("RGB")

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)

    if output_abs_path is None:
        base, ext = os.path.splitext(input_abs_path)
        output_abs_path = f"{base}_b{brightness}_c{contrast}{ext}"

    img.save(output_abs_path)
    return output_abs_path


if __name__ == "__main__":
    out = adjust_brightness_contrast(
        input_abs_path="/Users/hdd/Desktop/python-code/墨以数字/collection_compiler_backend/test/77A00101A08A10B12007D58472.jpg",
        output_abs_path="/Users/hdd/Desktop/python-code/墨以数字/collection_compiler_backend/test/out2.jpg",
        brightness=1,
        contrast=1.8
    )
    print("保存到:", out)
