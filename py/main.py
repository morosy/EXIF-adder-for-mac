import sys
from pathlib import Path
from math import gcd

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL.ExifTags import TAGS
import exifread

EXIF_TAG_ORIENTATION = 274


def format_date(date_string):
    if not date_string or " " not in str(date_string):
        return "N/A"
    date_part = str(date_string).split(" ")[0]
    return date_part.replace(":", ".")


def _to_float(value):
    try:
        return float(value)
    except Exception:
        pass

    if isinstance(value, tuple) and len(value) == 2:
        num, den = value
        try:
            return float(num) / float(den)
        except Exception:
            return None

    try:
        return float(value)
    except Exception:
        return None


def convert_to_fraction(decimal_value):
    if not isinstance(decimal_value, (float, int)):
        return "N/A"

    denominator = 1
    limit = 10 ** 7
    while (decimal_value * denominator) % 1 != 0 and denominator < limit:
        denominator *= 10

    numerator = int(decimal_value * denominator)
    common_divisor = gcd(numerator, denominator)
    numerator //= common_divisor
    denominator //= common_divisor
    return f"{numerator}/{denominator}"


def _get_exif_dict_pillow(image_path: Path):
    try:
        img = Image.open(image_path)
    except Exception:
        return None

    exif_data = None
    try:
        exif_data = img._getexif()
    except Exception:
        exif_data = None

    if exif_data:
        exif_dict = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
        return exif_dict

    try:
        exif = img.getexif()
        if exif:
            exif_dict = {TAGS.get(tag, tag): exif.get(tag) for tag in exif.keys()}
            return exif_dict
    except Exception:
        pass

    return None


def _select_exif(exif_data: dict):
    target_keys = {
        "DateTimeOriginal": "Date",
        "Model": "Camera Model",
        "ISOSpeedRatings": "ISO",
        "FocalLength": "Focal Length (mm)",
        "FNumber": "F-Number",
        "ExposureTime": "Shutter Speed (s)",
    }

    selected = {label: exif_data.get(key, "N/A") for key, label in target_keys.items()}

    if selected.get("Date") != "N/A":
        selected["Date"] = format_date(selected["Date"])

    ss = selected.get("Shutter Speed (s)")
    if ss != "N/A":
        ss_float = _to_float(ss)
        if ss_float is None:
            selected["Shutter Speed (s)"] = "N/A"
        else:
            selected["Shutter Speed (s)"] = convert_to_fraction(ss_float)

    fl = selected.get("Focal Length (mm)")
    if fl != "N/A":
        fl_float = _to_float(fl)
        selected["Focal Length (mm)"] = "N/A" if fl_float is None else f"{fl_float:.0f}"

    fn = selected.get("F-Number")
    if fn != "N/A":
        fn_float = _to_float(fn)
        selected["F-Number"] = "N/A" if fn_float is None else f"f/{fn_float:.1f}"

    return selected


def _build_overlay_text(selected: dict) -> str:
    date = selected.get("Date", "N/A")
    model = selected.get("Camera Model", "N/A")
    iso = selected.get("ISO", "N/A")
    fl = selected.get("Focal Length (mm)", "N/A")
    fn = selected.get("F-Number", "N/A")
    ss = selected.get("Shutter Speed (s)", "N/A")

    parts = []
    parts.append(date)
    parts.append(model)
    parts.append(f"ISO{iso}" if iso != "N/A" else "ISO N/A")
    parts.append(f"{fl}mm" if fl != "N/A" else "N/Amm")
    parts.append(fn)
    parts.append(ss)

    return "  |  ".join([p for p in parts if p])


def read_exif_selected(image_path: Path) -> dict:
    exif = _get_exif_dict_pillow(image_path)
    if exif:
        return _select_exif(exif)

    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)

        selected = {
            "Date": str(tags.get("EXIF DateTimeOriginal", "N/A")),
            "Camera Model": str(tags.get("Image Model", "N/A")),
            "ISO": str(tags.get("EXIF ISOSpeedRatings", "N/A")),
            "Focal Length (mm)": str(tags.get("EXIF FocalLength", "N/A")),
            "F-Number": str(tags.get("EXIF FNumber", "N/A")),
            "Shutter Speed (s)": str(tags.get("EXIF ExposureTime", "N/A")),
        }

        if selected["Date"] != "N/A":
            selected["Date"] = format_date(selected["Date"])

        return selected
    except Exception as e:
        print(f"[EXIF] exifread fallback failed: {e}")
        return {
            "Date": "N/A",
            "Camera Model": "N/A",
            "ISO": "N/A",
            "Focal Length (mm)": "N/A",
            "F-Number": "N/A",
            "Shutter Speed (s)": "N/A",
        }


def add_frame_and_text(input_path: Path, output_path: Path):
    exif_bytes = None
    with Image.open(input_path) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
        try:
            exif = src.getexif()
            if exif:
                exif[EXIF_TAG_ORIENTATION] = 1
                exif_bytes = exif.tobytes()
        except Exception:
            exif_bytes = src.info.get("exif")

    selected = read_exif_selected(input_path)

    exif_ok = any(v != "N/A" for v in selected.values())
    print(f"[EXIF_OK] {'true' if exif_ok else 'false'}")

    print("[EXIF] Selected fields:")
    for k, v in selected.items():
        print(f"[EXIF] {k}: {v}")

    overlay_text = _build_overlay_text(selected)

    w, h = img.size
    pad_lr = int(max(w, h) * 0.04)
    pad_top = int(max(w, h) * 0.04)
    pad_bottom = int(max(w, h) * 0.12)

    new_w = w + pad_lr * 2
    new_h = h + pad_top + pad_bottom

    canvas = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    canvas.paste(img, (pad_lr, pad_top))

    draw = ImageDraw.Draw(canvas)

    font_size = max(12, int(max(w, h) * 0.028))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), overlay_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (new_w - text_w) // 2
    y = h + pad_top + (pad_bottom - text_h) // 2

    draw.text((x, y), overlay_text, fill=(0, 0, 0), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"quality": 95}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    canvas.save(output_path, **save_kwargs)


def main():
    if len(sys.argv) < 3:
        print("Usage: python main.py <input_image> <output_image>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    add_frame_and_text(input_path, output_path)

    print(f"[OK] Output: {output_path}")


if __name__ == "__main__":
    main()
