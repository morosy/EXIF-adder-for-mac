import sys
from pathlib import Path
from math import gcd, ceil

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL.ExifTags import TAGS
import exifread

EXIF_TAG_ORIENTATION = 274

ASPECT_RATIOS = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3": (4, 3),
    "3:4": (3, 4),
    "5:4": (5, 4),
    "4:5": (4, 5),
    "1:1": (1, 1),
}


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


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _line_height(font: ImageFont.ImageFont) -> int:
    # ascent + descent を「行ボックス」として扱う（見た目の上下差が出にくい）
    try:
        ascent, descent = font.getmetrics()
        return int(ascent + descent)
    except Exception:
        # fallback
        return int(getattr(font, "size", 14))


def _build_exif_lines(selected: dict) -> tuple[str, str, str]:
    # 構成：機種名 → 日付 → 詳細
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


def _parse_aspect(argv: list[str]) -> str | None:
    if "--aspect" not in argv:
        return None
    i = argv.index("--aspect")
    if i + 1 >= len(argv):
        return None
    return argv[i + 1]


def add_frame_and_text(input_path: Path, output_path: Path, aspect: str | None):
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

    if aspect:
        print(f"[ASPECT] Requested: {aspect}")
    else:
        print("[ASPECT] Requested: (none)")

    # ---- 3段テキスト（機種名→日付→詳細） ----
    model_line, date_line, details_line = _build_exif_lines(selected)

    w, h = img.size
    base = max(w, h)

    # 左右余白（外枠）
    pad_lr = int(base * 0.04)

    # フォントサイズ：機種名 > 日付 = その他
    model_size = max(14, int(base * 0.032))
    other_size = max(12, int(base * 0.026))

    font_model = _load_font(model_size)
    font_date = _load_font(other_size)
    font_details = _load_font(other_size)

    # 行間：もう少し広く
    line_gap = max(12, int(base * 0.016))

    # 行ボックス高さ
    lh_model = _line_height(font_model)
    lh_date = _line_height(font_date)
    lh_details = _line_height(font_details)

    # テキストブロック高さ（行ボックス基準）
    block_h = lh_model + line_gap + lh_date + line_gap + lh_details

    # ✅ あなたの定義する「EXIF上下余白」を固定（上部=下部）
    # 上部=画像下端〜1行目行ボックス上端
    # 下部=最終行行ボックス下端〜出力画像下端
    exif_pad_min = int(base * 0.035)
    exif_pad = max(exif_pad_min, int(other_size * 1.4))

    # 画像上の外側余白（ここは「EXIF上下余白」ではない）
    top_outer = int(base * 0.04)

    # ---- まず「比率を考慮しない最小キャンバス」寸法を作る ----
    min_w = w + pad_lr * 2
    min_h = top_outer + h + exif_pad + block_h + exif_pad

    # ---- 比率指定があれば、最終キャンバスをその比率に拡張（外側余白を作らない） ----
    final_w = min_w
    final_h = min_h

    if aspect and aspect in ASPECT_RATIOS:
        aw, ah = ASPECT_RATIOS[aspect]
        ratio = aw / ah

        # min_w / min_h と ratio を比較して、どちらかを増やす（トリミングなし）
        if (min_w / min_h) > ratio:
            # 横長すぎ → 高さを増やす
            target_h = int(ceil(min_w / ratio))
            extra_h = target_h - min_h
            # ✅ 外側に足すのではなく、EXIF上下余白に均等に配分して「上下余白の定義」を崩さない
            add_each = extra_h // 2
            exif_pad = exif_pad + add_each
            # 余りが出たら下側に1足す（見た目優先で僅差をなくす）
            remainder = extra_h - add_each * 2

            final_w = min_w
            final_h = top_outer + h + exif_pad + block_h + exif_pad + remainder
        else:
            # 縦長すぎ → 幅を増やす（左右に足す：EXIF上下余白には影響しない）
            target_w = int(ceil(min_h * ratio))
            extra_w = target_w - min_w
            add_lr = extra_w // 2
            remainder = extra_w - add_lr * 2
            pad_lr = pad_lr + add_lr
            final_w = w + pad_lr * 2 + remainder
            final_h = min_h
    else:
        final_w = min_w
        final_h = min_h

    print(f"[LAYOUT] pad_lr={pad_lr} top_outer={top_outer} exif_pad={exif_pad} line_gap={line_gap}")
    print(f"[LAYOUT] min=({min_w}x{min_h}) final=({final_w}x{final_h}) block_h={block_h}")

    # ---- 描画開始 ----
    canvas = Image.new("RGB", (final_w, final_h), (255, 255, 255))

    img_x = pad_lr
    img_y = top_outer
    canvas.paste(img, (img_x, img_y))

    draw = ImageDraw.Draw(canvas)

    # テキストブロック開始（あなた定義の上部余白 = exif_pad）
    block_top = img_y + h + exif_pad

    cx = final_w // 2

    # 各行の中心Yを決める（anchor="mm"で行ボックス中央に配置）
    y_model_c = block_top + (lh_model // 2)
    y_date_c = block_top + lh_model + line_gap + (lh_date // 2)
    y_details_c = block_top + lh_model + line_gap + lh_date + line_gap + (lh_details // 2)

    # Pillowのanchorを使って確実に中央揃え
    draw.text((cx, y_model_c), model_line, fill=(0, 0, 0), font=font_model, anchor="mm")
    draw.text((cx, y_date_c), date_line, fill=(0, 0, 0), font=font_date, anchor="mm")
    draw.text((cx, y_details_c), details_line, fill=(0, 0, 0), font=font_details, anchor="mm")

    # デバッグ（あなたの定義の余白が一致することを数値で出す）
    top_exif_margin = block_top - (img_y + h)
    bottom_exif_margin = final_h - (block_top + block_h)
    print(f"[MARGIN] top_exif={top_exif_margin} bottom_exif={bottom_exif_margin}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"quality": 95}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    canvas.save(output_path, **save_kwargs)


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python main.py <input_image> <output_image> "
            "[--aspect 16:9|9:16|4:3|3:4|5:4|4:5|1:1]"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    aspect = _parse_aspect(sys.argv[3:])

    add_frame_and_text(input_path, output_path, aspect)
    print(f"[OK] Output: {output_path}")


if __name__ == "__main__":
    main()
