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
    r = ratio_of(aspect)
    if (min_w / min_h) > r:
        target_h = int(ceil(min_w / r))
        return min_w, target_h
    target_w = int(ceil(min_h * r))
    return target_w, min_h
