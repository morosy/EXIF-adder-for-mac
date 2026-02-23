import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import exifread

def read_exif_summary(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    dt = str(tags.get("EXIF DateTimeOriginal", "Unknown Date"))
    make = str(tags.get("Image Make", ""))
    model = str(tags.get("Image Model", ""))

    camera = (make + " " + model).strip() if (make or model) else "Unknown Camera"
    return f"{dt}  |  {camera}"

def add_frame_and_text(input_path: Path, output_path: Path):
    img = Image.open(input_path).convert("RGB")
    w, h = img.size

    pad_lr = int(max(w, h) * 0.04)
    pad_top = int(max(w, h) * 0.04)
    pad_bottom = int(max(w, h) * 0.12)

    new_w = w + pad_lr * 2
    new_h = h + pad_top + pad_bottom

    canvas = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    canvas.paste(img, (pad_lr, pad_top))

    text = read_exif_summary(input_path)
    draw = ImageDraw.Draw(canvas)

    # まずはmac標準フォントを試す（将来は同梱推奨）
    font_size = max(12, int(max(w, h) * 0.03))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (new_w - text_w) // 2
    y = h + pad_top + (pad_bottom - text_h) // 2

    draw.text((x, y), text, fill=(0, 0, 0), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, quality=95)

def main():
    if len(sys.argv) < 3:
        print("Usage: python main.py <input_image> <output_image>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    add_frame_and_text(input_path, output_path)
    print(f"OK: {output_path}")

if __name__ == "__main__":
    main()
