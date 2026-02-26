from __future__ import annotations

from math import ceil

ASPECT_RATIOS: dict[str, tuple[int, int]] = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3": (4, 3),
    "3:4": (3, 4),
    "5:4": (5, 4),
    "4:5": (4, 5),
    "1:1": (1, 1),
}


def is_supported(aspect: str | None) -> bool:
    return bool(aspect) and aspect in ASPECT_RATIOS


def ratio_of(aspect: str) -> float:
    aw, ah = ASPECT_RATIOS[aspect]
    return aw / ah


def expand_to_aspect(min_w: int, min_h: int, aspect: str) -> tuple[int, int]:
    """
    min_w/min_h を満たしつつ、指定比率になるように拡張した (w,h) を返す（トリミングなし）。
    """
    r = ratio_of(aspect)
    if (min_w / min_h) > r:
        # 横長すぎ → 高さを増やす
        target_h = int(ceil(min_w / r))
        return min_w, target_h
    # 縦長すぎ → 幅を増やす
    target_w = int(ceil(min_h * r))
    return target_w, min_h
