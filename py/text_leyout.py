from __future__ import annotations

from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size)
    except Exception:
        return ImageFont.load_default()


def line_height(font: ImageFont.ImageFont) -> int:
    try:
        ascent, descent = font.getmetrics()
        return int(ascent + descent)
    except Exception:
        return int(getattr(font, "size", 14))


@dataclass(frozen=True)
class ExifTextLayout:
    model_font: ImageFont.ImageFont
    other_font: ImageFont.ImageFont
    line_gap: int
    lh_model: int
    lh_other: int
    block_h: int


def make_layout(base: int) -> ExifTextLayout:
    # 機種名 > 日付=その他
    model_size = max(14, int(base * 0.032))
    other_size = max(12, int(base * 0.026))

    model_font = load_font(model_size)
    other_font = load_font(other_size)

    line_gap = max(12, int(base * 0.016))

    lh_model = line_height(model_font)
    lh_other = line_height(other_font)

    block_h = lh_model + line_gap + lh_other + line_gap + lh_other

    return ExifTextLayout(
        model_font=model_font,
        other_font=other_font,
        line_gap=line_gap,
        lh_model=lh_model,
        lh_other=lh_other,
        block_h=block_h,
    )


def draw_centered_3lines(
    canvas: Image.Image,
    cx: int,
    top_y: int,
    model_line: str,
    date_line: str,
    details_line: str,
    layout: ExifTextLayout,
) -> tuple[int, int]:
    """
    top_y をテキストブロック上端として、行ボックス基準で3行を中央配置して描画。
    戻り値： (block_top, block_bottom)
    """
    draw = ImageDraw.Draw(canvas)

    y_model_c = top_y + (layout.lh_model // 2)
    y_date_c = top_y + layout.lh_model + layout.line_gap + (layout.lh_other // 2)
    y_details_c = top_y + layout.lh_model + layout.line_gap + layout.lh_other + layout.line_gap + (layout.lh_other // 2)

    draw.text((cx, y_model_c), model_line, fill=(0, 0, 0), font=layout.model_font, anchor="mm")
    draw.text((cx, y_date_c), date_line, fill=(0, 0, 0), font=layout.other_font, anchor="mm")
    draw.text((cx, y_details_c), details_line, fill=(0, 0, 0), font=layout.other_font, anchor="mm")

    return top_y, top_y + layout.block_h
