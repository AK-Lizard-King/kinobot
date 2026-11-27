#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Logic tests for the fork's frame helpers.

The package import is broken on master (`kinobot/__init__.py` imports a
top-level `config` module), so these tests load the helper files directly.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    path = ROOT / "kinobot" / ("%s.py" % name)
    spec = importlib.util.spec_from_file_location("fork_%s" % name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tonemap = _load("tonemap")
quotes = _load("quote_match")
frames = _load("frameops")


PROBE_PQ = """
{"streams":[{"color_transfer":"smpte2084","color_primaries":"bt2020",
"color_space":"bt2020nc","side_data_list":[{"side_data_type":"Mastering display metadata"}]}]}
"""
PROBE_HLG = '{"streams":[{"color_transfer":"arib-std-b67"}]}'
PROBE_DV = '{"streams":[{"side_data_list":[{"side_data_type":"DOVI configuration record"}]}]}'
PROBE_SDR = '{"streams":[{"color_transfer":"bt709","color_primaries":"bt709"}]}'


def test_probe_classifies_hdr_and_sdr():
    assert tonemap.probe_is_hdr(PROBE_PQ) is True
    assert tonemap.classify_probe(PROBE_PQ) == (True, "pq")
    assert tonemap.classify_probe(PROBE_HLG) == (True, "hlg")
    assert tonemap.classify_probe(PROBE_DV)[0] is True
    assert tonemap.probe_is_hdr(PROBE_SDR) is False
    assert tonemap.probe_is_hdr("dolby vision profile 5") is True


def test_tonemap_chain_placebo_zscale_and_fallback():
    placebo = tonemap.sdr_tonemap_vf({"placebo": True, "zscale": True, "tonemap": True})
    assert placebo.startswith("libplacebo=")
    assert "apply_dolbyvision=1" in placebo
    assert "bt709" in placebo

    hable = tonemap.sdr_tonemap_vf({"zscale": True, "tonemap": True}, transfer="pq")
    assert "zscale=tin=smpte2084" in hable
    assert "tonemap=tonemap=hable:desat=0" in hable
    assert "zscale=t=bt709:m=bt709:r=tv" in hable
    assert "format=yuv420p" in hable

    hlg = tonemap.sdr_tonemap_vf({"zscale": True, "tonemap": True}, transfer="hlg")
    assert "zscale=tin=arib-std-b67" in hlg

    fast = tonemap.sdr_tonemap_vf(
        {"zscale": True, "tonemap": True}, preset="fast", max_w=1280
    )
    assert fast.startswith("scale='min(1280,iw)':-2:flags=bilinear,")
    assert "tonemap=tonemap=reinhard:desat=0" in fast

    bare = tonemap.sdr_tonemap_vf({})
    assert bare == "tonemap=hable:desat=0,format=yuv420p"


def test_extract_args_add_tonemap_only_for_hdr():
    sdr = tonemap.build_extract_args("movie.mkv", "12.0", "out.png", hdr=False, caps={})
    assert "tonemap" not in " ".join(sdr)
    assert sdr[sdr.index("-vf") + 1] == "scale=iw*sar:ih"
    assert "-init_hw_device" not in sdr

    caps = {"placebo": True, "zscale": True, "tonemap": True}
    hdr = tonemap.build_extract_args(
        "movie.mkv", "12.0", "out.png", hdr=True, caps=caps, transfer="pq"
    )
    assert hdr[1:3] == ["-init_hw_device", "vulkan"]
    vf = hdr[hdr.index("-vf") + 1]
    assert vf.startswith("libplacebo=")
    assert vf.endswith(",scale=iw*sar:ih")

    z = tonemap.build_extract_args(
        "movie.mkv",
        "1.500",
        "out.png",
        hdr=True,
        caps={"zscale": True, "tonemap": True},
        transfer="hlg",
        tail="subtitles='film.mkv',scale=iw*sar:ih",
    )
    vf = z[z.index("-vf") + 1]
    assert "zscale=tin=arib-std-b67" in vf
    assert vf.endswith("subtitles='film.mkv',scale=iw*sar:ih")
    assert "-init_hw_device" not in z


def test_zoom_flags_and_corner_geometry():
    folded = frames.prepare_frame_flags({"tl": True, "font": "clearsans"})
    assert folded["zoom_corner"] == "tl"
    assert "tl" not in folded
    assert folded["font"] == "clearsans"

    moved = frames.prepare_frame_flags({"position": "top-left", "tr": True})
    assert moved["text_position"] == "top-left"
    assert moved["zoom_corner"] == "tr"

    try:
        frames.prepare_frame_flags({"tl": True, "br": True})
    except ValueError as error:
        assert "one corner" in str(error)
    else:
        raise AssertionError("two corners should fail")

    size, box = frames.zoom_geometry(200, 100, 2, None)
    assert size == (400, 200)
    assert box == (100, 50, 300, 150)
    assert frames.zoom_geometry(200, 100, 2, "tl")[1] == (0, 0, 200, 100)
    assert frames.zoom_geometry(200, 100, 2, "br")[1] == (200, 100, 400, 200)
    assert frames.DEFAULT_CORNER_ZOOM == 2.0


def test_text_position_and_rewrap():
    assert frames.normalize_position("TL") == "tl"
    assert frames.normalize_position("top-right") == "tr"
    assert frames.normalize_position("centre") == "c"
    assert frames.normalize_position("BC") == "bc"
    assert frames.normalize_position("nope") is None
    assert frames.normalize_position(None) is None

    x, y = frames.quote_origin(1000, 500, 200, 40, y_offset=15, position="bc")
    assert x == (1000 - 200) / 2
    assert y == 500 - 40 - int(0.15 * 500)

    left, _ = frames.quote_origin(1000, 500, 200, 40, align="left", position="bc")
    assert left == max(int(1000 * 0.04), 8)
    right, top = frames.quote_origin(1000, 500, 200, 40, position="tr", y_offset=10)
    assert right == 1000 - max(int(1000 * 0.04), 8) - 200
    assert top == int(0.10 * 500)

    wrapped = frames.rewrap_text("one two three four five six seven eight", 0.5)
    assert "\n" in wrapped
    assert max(len(line) for line in wrapped.split("\n")) < len(wrapped.replace("\n", " "))


def test_quote_ranking_and_occurrence():
    cues = [
        "I hardly know her.",
        "Hello there.",
        "Well, hello there, friend.",
        "Hello there.",
        "A start, not the art.",
    ]
    index, cleaned, error = quotes.pick_quote("Hello there.", cues)
    assert error is None
    assert cleaned == "Hello there."
    assert index == 1

    index, _, error = quotes.pick_quote("hello there #2", cues)
    assert error is None
    assert index == 3

    index, _, error = quotes.pick_quote("Hello there #3", cues)
    assert index is None
    assert error and "#3" in error

    index, _, error = quotes.pick_quote("tar", cues)
    assert error is None
    assert index is None  # "tar" only sits inside "start", not as a word

    index, _, _ = quotes.pick_quote("hardly know", cues)
    assert index == 0


def test_display_dimensions_and_aspect_crop():
    assert frames.display_dimensions(1920, 1080, 16 / 9) == (1920, 1080)
    assert frames.display_dimensions(1440, 1080, 16 / 9) == (1920, 1080)
    # 720x480 stored, 4:3 displayed: width becomes height * DAR (640), not a stretch of both axes.
    assert frames.display_dimensions(720, 480, 4 / 3) == (640, 480)

    box = frames.aspect_crop_box(1920, 800, 16 / 9, x_off=100, y_off=-100)
    left, top, right, bottom = box
    assert 0 <= left < right <= 1920
    assert 0 <= top < bottom <= 800
    ratio = (right - left) / float(bottom - top)
    assert abs(ratio - (16 / 9)) < 0.05

    try:
        frames.aspect_crop_box(100, 100, 100)
    except ValueError as error:
        assert "aspect quotient" in str(error)
    else:
        raise AssertionError("extreme ratio should fail")
