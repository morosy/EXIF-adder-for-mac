from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from aspect import ASPECT_RATIOS, is_supported, expand_to_aspect
from exif_reader import read_exif_selected, exif_ok, build_lines
from text_layout import make_layout, draw_centered_3lines

EXIF_TAG_ORIENTATION = 274


def _fit_image_contain(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    w, h = img.size
    if w <= 0 or h <= 0:
        return img

    scale_w = max_w / w
    scale_h = max_h / h
    scale = min(scale_w, scale_h)

    if scale >= 1.0:
        return img

    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def render_image(input_path: Path, output_path: Path, aspect: str | None) -> tuple[bool, str]:
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
    input_ratio = (w / h) if h != 0 else 1.0

    selected = read_exif_selected(input_path)
    ok = exif_ok(selected)

    logs.append(f"[EXIF_OK] {'true' if ok else 'false'}")
    logs.append("[EXIF] Selected fields:")
    for k, v in selected.items():
        logs.append(f"[EXIF] {k}: {v}")

    model_line, date_line, details_line = build_lines(selected)

    pad_lr = int(base * 0.04)
    top_outer = int(base * 0.04)

    layout = make_layout(base)

    exif_pad_min = int(base * 0.035)
    exif_pad = max(exif_pad_min, int(getattr(layout.other_font, "size", 12) * 1.4))

    aspect_is_landscape = False
    if is_supported(aspect):
        aw, ah = ASPECT_RATIOS[aspect]
        aspect_is_landscape = (aw / ah) > 1.0

    if not is_supported(aspect):
        use_legacy = input_ratio > 1.0
    else:
        use_legacy = aspect_is_landscape

    if use_legacy:
        min_w = w + pad_lr * 2
        min_h = top_outer + h + exif_pad + layout.block_h + exif_pad

        final_w = min_w
        final_h = min_h

        if is_supported(aspect):
            target_w, target_h = expand_to_aspect(min_w, min_h, aspect)
            extra_w = target_w - min_w
            extra_h = target_h - min_h

            if extra_w > 0:
                add_lr = extra_w // 2
                remainder = extra_w - add_lr * 2
                pad_lr = pad_lr + add_lr
                final_w = w + pad_lr * 2 + remainder
            else:
                final_w = min_w

            if extra_h > 0:
                add_each = extra_h // 2
                remainder = extra_h - add_each * 2
                exif_pad = exif_pad + add_each
                final_h = top_outer + h + exif_pad + layout.block_h + exif_pad + remainder
            else:
                final_h = min_h

            logs.append("[MODE] landscape / legacy")
            logs.append(f"[ASPECT] Requested: {aspect}")
            logs.append(f"[ASPECT] min=({min_w}x{min_h}) target=({target_w}x{target_h}) final=({final_w}x{final_h})")
        else:
            logs.append("[MODE] landscape / legacy")
            logs.append("[ASPECT] Requested: (none)")
            logs.append(f"[ASPECT] min=({min_w}x{min_h}) final=({final_w}x{final_h})")

        logs.append(f"[LAYOUT] pad_lr={pad_lr} top_outer={top_outer} exif_pad={exif_pad} line_gap={layout.line_gap}")

        canvas = Image.new("RGB", (final_w, final_h), (255, 255, 255))

        img_x = pad_lr
        img_y = top_outer
        canvas.paste(img, (img_x, img_y))

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
    else:
        logs.append("[MODE] canvas-first / center-of-canvas")

        bottom_margin = exif_pad + layout.block_h + exif_pad

        min_w = w + pad_lr * 2
        min_h = top_outer + h + bottom_margin

        final_w = min_w
        final_h = min_h

        if is_supported(aspect):
            target_w, target_h = expand_to_aspect(min_w, min_h, aspect)
            final_w, final_h = target_w, target_h
            logs.append(f"[ASPECT] Requested: {aspect}")
            logs.append(f"[ASPECT] min=({min_w}x{min_h}) target=({target_w}x{target_h})")
        else:
            logs.append("[ASPECT] Requested: (none)")
            logs.append(f"[ASPECT] min=({min_w}x{min_h})")

        canvas = Image.new("RGB", (final_w, final_h), (255, 255, 255))

        max_img_w = max(1, final_w - pad_lr * 2)
        max_img_h = max(1, final_h - bottom_margin - top_outer)
        fitted = _fit_image_contain(img, max_img_w, max_img_h)
        fw, fh = fitted.size

        img_x = (final_w - fw) // 2
        img_y_center = (final_h - fh) // 2
        img_y = max(top_outer, img_y_center)

        canvas.paste(fitted, (img_x, img_y))

        bottom_top = final_h - bottom_margin
        exif_top = bottom_top + (bottom_margin - layout.block_h) // 2
        cx = final_w // 2

        block_top_y, block_bottom_y = draw_centered_3lines(
            canvas,
            cx,
            exif_top,
            model_line,
            date_line,
            details_line,
            layout,
        )

        top_in_margin = block_top_y - bottom_top
        bottom_in_margin = final_h - block_bottom_y

        logs.append(
            f"[PLACEMENT] fitted=({fw}x{fh}) img_pos=({img_x},{img_y}) canvas=({final_w}x{final_h}) bottom_margin={bottom_margin}"
        )
        logs.append(f"[MARGIN] in_bottom_margin_top={top_in_margin} in_bottom_margin_bottom={bottom_in_margin}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"quality": 95}
    if exif_bytes:
        save_kwargs["exif"] = exif_bytes
    canvas.save(output_path, **save_kwargs)

    return ok, "\n".join(logs)
