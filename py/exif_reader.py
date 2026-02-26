from __future__ import annotations

from pathlib import Path
from math import gcd

from PIL import Image
from PIL.ExifTags import TAGS
import exifread


def format_date(date_string) -> str:
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


def _to_fraction(decimal_value: float) -> str:
    denominator = 1
    limit = 10 ** 7
    while (decimal_value * denominator) % 1 != 0 and denominator < limit:
        denominator *= 10

    numerator = int(decimal_value * denominator)
    common_divisor = gcd(numerator, denominator)
    numerator //= common_divisor
    denominator //= common_divisor
    return f"{numerator}/{denominator}"


def _get_exif_dict_pillow(image_path: Path) -> dict | None:
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
        return {TAGS.get(tag, tag): value for tag, value in exif_data.items()}

    try:
        exif = img.getexif()
        if exif:
            return {TAGS.get(tag, tag): exif.get(tag) for tag in exif.keys()}
    except Exception:
        pass

    return None


def _select_exif(exif_data: dict) -> dict:
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
        selected["Shutter Speed (s)"] = "N/A" if ss_float is None else _to_fraction(ss_float)

    fl = selected.get("Focal Length (mm)")
    if fl != "N/A":
        fl_float = _to_float(fl)
        selected["Focal Length (mm)"] = "N/A" if fl_float is None else f"{fl_float:.0f}"

    fn = selected.get("F-Number")
    if fn != "N/A":
        fn_float = _to_float(fn)
        selected["F-Number"] = "N/A" if fn_float is None else f"f/{fn_float:.1f}"

    return selected


def read_exif_selected(image_path: Path) -> dict:
    exif = _get_exif_dict_pillow(image_path)
    if exif:
        return _select_exif(exif)

    # fallback
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


def exif_ok(selected: dict) -> bool:
    return any(v != "N/A" for v in selected.values())


def build_lines(selected: dict) -> tuple[str, str, str]:
    """
    構成：
    機種名
    日付
    焦点距離 ISO F値 SS
    """
    model = selected.get("Camera Model", "N/A")
    date = selected.get("Date", "N/A")

    fl = selected.get("Focal Length (mm)", "N/A")
    iso = selected.get("ISO", "N/A")
    fn = selected.get("F-Number", "N/A")
    ss = selected.get("Shutter Speed (s)", "N/A")

    parts = []
    parts.append(f"{fl}mm" if fl != "N/A" else "N/Amm")
    parts.append(f"ISO{iso}" if iso != "N/A" else "ISO N/A")
    parts.append(fn)
    parts.append(ss)

    details = "  ".join([p for p in parts if p])
    return model, date, details
