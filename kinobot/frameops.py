#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License: GPL-3.0
# Original Kinobot by Vitiko <vhnz98@gmail.com>
#
# Geometry and flag folding for frames: corner zoom, caption position,
# aspect-quotient crop boxes, and display-aspect size. No image libraries.

import textwrap

ZOOM_CORNERS = ("tl", "tr", "bl", "br")
DEFAULT_CORNER_ZOOM = 2.0
POSITIONS = ("tl", "tr", "bl", "br", "tc", "c", "bc")
_POSITION_ALIASES = {
    "center": "c",
    "centre": "c",
    "middle": "c",
    "mc": "c",
    "cc": "c",
    "top": "tc",
    "bottom": "bc",
    "topleft": "tl",
    "top-left": "tl",
    "topright": "tr",
    "top-right": "tr",
    "bottomleft": "bl",
    "bottom-left": "bl",
    "bottomright": "br",
    "bottom-right": "br",
    "t": "tc",
    "b": "bc",
}
CORNER_MAX_W = 0.58


def prepare_frame_flags(data):
    """Fold `--tl`/`--position` spellings into model fields.

    Raises ValueError when more than one zoom corner is set in the same scope.
    A corner without `--zoom-factor` is left for the renderer, which zooms 2x.
    """
    folded = dict(data or {})
    if "position" in folded and "text_position" not in folded:
        folded["text_position"] = folded.pop("position")
    else:
        folded.pop("position", None)
    got = [corner for corner in ZOOM_CORNERS if folded.pop(corner, None)]
    if len(got) > 1:
        raise ValueError("Pick one corner: --tl, --tr, --bl or --br.")
    if got:
        folded["zoom_corner"] = got[0]
    return folded


def normalize_position(raw):
    """`TL` / `top-left` / `center` -> a canonical position, or None."""
    if raw is None or raw is True:
        return None
    value = str(raw).strip().strip("'\"").rstrip("]").lower().replace("_", "")
    value = _POSITION_ALIASES.get(value, value)
    if value in POSITIONS:
        return value
    return None


def rewrap_text(text, ratio):
    """Narrower line breaks. Each line becomes about `ratio` of the longest line."""
    words = " ".join(str(text or "").split())
    longest = max((len(line) for line in str(text or "").split("\n")), default=len(words))
    width = max(10, int(longest * ratio))
    return textwrap.fill(words, width=width, break_long_words=False)


def zoom_geometry(width, height, zoom_factor, corner=None):
    """(resized_size, crop_box) for a zoom that keeps the original frame size.

    The crop is centered unless corner is tl, tr, bl, or br.
    """
    width = int(width)
    height = int(height)
    factor = float(zoom_factor)
    new_width = int(width * factor)
    new_height = int(height * factor)
    x = int((new_width - width) / 2)
    y = int((new_height - height) / 2)
    spot = str(corner or "").lower()
    if spot in ZOOM_CORNERS:
        x = 0 if spot[1] == "l" else new_width - width
        y = 0 if spot[0] == "t" else new_height - height
    return (new_width, new_height), (x, y, x + width, y + height)


def display_dimensions(width, height, dar):
    """Pixel size that shows `dar` (width/height) without changing the frame height.

    Square pixels (the stored size already matches the DAR) are returned unchanged.
    Anamorphic frames grow or shrink the width only, which is what `scale=iw*sar:ih` does.
    """
    width = int(width)
    height = int(height)
    if width <= 0 or height <= 0 or not dar or float(dar) <= 0:
        return width, height
    display_w = max(1, int(round(height * float(dar))))
    if display_w == width:
        return width, height
    return display_w, height


def clamp_crop_box(box, width, height):
    """Force a crop box inside the frame and at least one pixel in each direction."""
    left, top, right, bottom = [float(value) for value in box]
    width = int(width)
    height = int(height)
    left = max(0.0, min(float(width - 1), left))
    top = max(0.0, min(float(height - 1), top))
    right = max(left + 1.0, min(float(width), right))
    bottom = max(top + 1.0, min(float(height), bottom))
    return (int(left), int(top), int(round(right)), int(round(bottom)))


def aspect_crop_box(width, height, threshold, x_off=0, y_off=0):
    """Crop box for an aspect quotient, plus the x/y offsets (percent of the trimmed margin).

    Same walk as the original crop: step 7 pixels until the ratio is within 0.03.
    The box is clamped so an offset cannot leave the frame.
    Raises ValueError when the ratio cannot be reached.
    """
    width = int(width)
    height = int(height)
    init_w, init_h = width, height
    if init_w <= 0 or init_h <= 0:
        raise ValueError("That aspect quotient can't be reached for this frame.")
    quotient = width / float(height)
    threshold = float(threshold)
    crop_tuple = (0, 0, init_w, init_h)
    for _inc in range(1, 502):
        if quotient > threshold:
            width -= 7
            if width <= 0 or init_h <= 0:
                break
            quotient = (width - (init_w - width)) / float(init_h)
            crop_tuple = (init_w - width, 0, width, init_h)
        else:
            height -= 7
            off = init_h - height
            denom = init_h - off
            if height <= 0 or denom <= 0:
                break
            quotient = init_w / float(denom)
            crop_tuple = (0, off / 2.0, init_w, init_h - (off / 2.0))
        if abs(quotient - threshold) < 0.03:
            crop_tuple = list(crop_tuple)
            if x_off:
                offset = crop_tuple[0] * (float(x_off) / 100.0)
                crop_tuple[0] = crop_tuple[0] + offset
                crop_tuple[2] = crop_tuple[2] + offset
            if y_off:
                offset = crop_tuple[1] * (float(y_off) / 100.0)
                crop_tuple[1] = crop_tuple[1] - offset
                crop_tuple[3] = crop_tuple[3] - offset
            return clamp_crop_box(crop_tuple, init_w, init_h)
    raise ValueError("That aspect quotient can't be reached for this frame.")


def quote_origin(
    width,
    height,
    text_w,
    text_h,
    y_offset=15,
    align="center",
    position="bc",
    plus_y=0,
    block_top=None,
):
    """Top-left of one caption line.

    Bottom-centre with no extra position keeps the original placement:
    `y = height - text_h - y_offset%`, `x` centered. `--text-align` moves that
    line left or right. `--position` places the block (top, centre, or a corner).
    """
    width = float(width)
    height = float(height)
    text_w = float(text_w)
    text_h = float(text_h)
    off = int((float(y_offset) / 100.0) * height)
    margin = max(int(width * 0.04), 8)
    spot = position or "bc"
    horiz = None
    if spot == "c":
        horiz = "c"
    elif len(spot) == 2:
        horiz = spot[1]
    align = (align or "center").lower()
    if horiz == "l":
        x = margin
    elif horiz == "r":
        x = width - margin - text_w
    elif align == "left":
        x = margin
    elif align == "right":
        x = width - margin - text_w
    else:
        x = (width - text_w) / 2.0
    if spot in ("tl", "tc", "tr"):
        y = off + plus_y
    elif spot == "c":
        base = (height - text_h) / 2.0 if block_top is None else block_top
        y = base + plus_y
    else:
        y = (height - text_h - off) + plus_y
    return x, y
