from __future__ import annotations

from pathlib import Path
from math import ceil

from PIL import Image, ImageOps

from aspect import is_supported, expand_to_aspect
from exif_reader import read_exif_selected, exif_ok, build_lines
from text_layout import make_layout, draw_centered_3lines

EXIF_TAG_ORIENTATION = 274


def render_image(input_path: Path, output_path: Path, aspect: str | None) -> tuple[bool, str]:
    """
    画像に外枠＋EXIFテキストを追加して保存する。
    返り値：(exif_ok, debug_log_string)
    """
    logs: list[str] = []

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

    w, h = img.size
    base = max(w, h)

    selected = read_exif_selected(input_path)
    ok = exif_ok(selected)

    logs.append(f"[EXIF_OK] {'true' if ok else 'false'}")
    logs.append("[EXIF] Selected fields:")
    for k, v in selected.items():
        logs.append(f"[EXIF] {k}: {v}")

    model_line, date_line, details_line = build_lines(selected)

    # 余白・レイアウト
    pad_lr = int(base * 0.04)
    top_outer = int(base * 0.04)

    layout = make_layout(base)

    # あなた定義の「EXIF上下余白」を確保（上部=下部）
    exif_pad_min = int(base * 0.035)
    # 文字サイズに対して最低限を確保
    exif_pad = max(exif_pad_min, int(getattr(layout.other_font, "size", 12) * 1.4))

    # 最小サイズ
    min_w = w + pad_lr * 2
    min_h = top_outer + h + exif_pad + layout.block_h + exif_pad

    final_w = min_w
    final_h = min_h

    if is_supported(aspect):
        target_w, target_h = expand_to_aspect(min_w, min_h, aspect)  # 拡張のみ
        extra_w = target_w - min_w
        extra_h = target_h - min_h

        # 幅増分 → 左右余白へ（EXIF余白に影響なし）
        if extra_w > 0:
            add_lr = extra_w // 2
            remainder = extra_w - add_lr * 2
            pad_lr = pad_lr + add_lr
            final_w = w + pad_lr * 2 + remainder
        else:
            final_w = min_w

        # 高さ増分 → EXIF上下余白へ均等配分（あなたの上下余白定義を崩さない）
        if extra_h > 0:
            add_each = extra_h // 2
            remainder = extra_h - add_each * 2
            exif_pad = exif_pad + add_each
            final_h = top_outer + h + exif_pad + layout.block_h + exif_pad + remainder
        else:
            final_h = min_h

        logs.append(f"[ASPECT] Requested: {aspect}")
        logs.append(f"[ASPECT] min=({min_w}x{min_h}) target=({target_w}x{target_h}) final=({final_w}x{final_h})")
    else:
        logs.append("[ASPECT] Requested: (none)")
        logs.append(f"[ASPECT] min=({min_w}x{min_h}) final=({final_w}x{final_h})")

    logs.append(f"[LAYOUT] pad_lr={pad_lr} top_outer={top_outer} exif_pad={exif_pad} line_gap={layout.line_gap}")

    # 描画
    canvas = Image.new("RGB", (final_w, final_h), (255, 255, 255))

    img_x = pad_lr
    img_y = top_outer
    canvas.paste(img, (img_x, img_y))

    # テキストブロック（上部余白=exif_pad）
    block_top = img_y + h + exif_pad
    cx = final_w // 2

    block_top_y, block_bottom_y = draw_centered_3lines(
        canvas,
        cx,
        block_top,
        model_line,
        date_line,
        details_line,
        layout,
    )

    top_exif_margin = block_top_y - (img_y + h)
    bottom_exif_margin = final_h - block_bottom_y
    logs.append(f"[MARGIN] top_exif={top_exif_margin} bottom_exif={bottom_exif_margin}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"quality": 95}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    canvas.save(output_path, **save_kwargs)

    return ok, "\n".join(logs)
