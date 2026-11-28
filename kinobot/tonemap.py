#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License: GPL-3.0
# Original Kinobot by Vitiko <vhnz98@gmail.com>
#
# HDR10 / HLG / Dolby Vision frames are tone-mapped to BT.709 SDR before the
# usual SAR scale. libplacebo (with Dolby Vision applied) is used when ffmpeg
# can actually run it. Otherwise the chain is zscale to linear light, a hable
# or reinhard tonemap, then BT.709. A bare tonemap is the last fallback.

import json
import os
import subprocess

_HDR_CACHE = {}
_CAPS_CACHE = None

_HDR_TOKENS = (
    "smpte2084",
    "arib-std-b67",
    "hlg",
    "dolby vision",
    "dovi",
    "smpte2086",
    "mastering display",
    "content light level",
)


def tonemap_mode(default="auto"):
    """KINOBOT_HDR_TONEMAP or the hdr_tonemap config key. auto, on, or off."""
    env = os.environ.get("KINOBOT_HDR_TONEMAP")
    if env is not None and str(env).strip():
        return str(env).strip().lower()
    try:
        from .config import config

        value = config.get("hdr_tonemap", None)
    except Exception:
        value = None
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower()


def _mode_forces(mode):
    mode = (mode or "auto").strip().lower()
    if mode in {"off", "0", "false", "no"}:
        return False
    if mode in {"on", "1", "true", "yes", "force"}:
        return True
    return None


def probe_is_hdr(blob):
    """True when ffprobe text or JSON describes an HDR or Dolby Vision stream."""
    return classify_probe(blob)[0]


def classify_probe(blob):
    """Return (is_hdr, transfer). transfer is 'hlg', 'pq', or None."""
    text = blob if isinstance(blob, str) else json.dumps(blob)
    folded = (text or "").lower()
    hdr = any(token in folded for token in _HDR_TOKENS)
    transfer = None
    if "arib-std-b67" in folded or '"hlg"' in folded or "transfer=hlg" in folded:
        transfer = "hlg"
    elif "smpte2084" in folded or "smpte2086" in folded:
        transfer = "pq"
    return hdr, transfer


def transfer_curve(transfer):
    """zscale input transfer. HLG uses arib-std-b67; PQ and unknown HDR use smpte2084."""
    if (transfer or "").lower() == "hlg":
        return "arib-std-b67"
    return "smpte2084"


def sdr_tonemap_vf(caps, max_w=None, preset="quality", transfer=None):
    """ffmpeg -vf piece that converts HDR to BT.709 SDR. caps keys: placebo, zscale, tonemap."""
    caps = caps or {}
    preset = (preset or "quality").strip().lower()
    fast = preset in {"fast", "still", "lite", "reinhard"}
    algo = "reinhard" if fast else "hable"
    prefix = ""
    if max_w and int(max_w) > 0:
        flags = ":flags=bilinear" if fast else ""
        prefix = "scale='min(%d,iw)':-2%s," % (int(max_w), flags)
    if caps.get("placebo"):
        return (
            prefix
            + "libplacebo=tonemapping=bt.2390:apply_dolbyvision=1:colorspace=bt709:"
            "color_primaries=bt709:color_trc=bt709:range=tv:format=yuv420p"
        )
    if caps.get("zscale") and caps.get("tonemap"):
        tin = transfer_curve(transfer)
        return (
            prefix
            + "zscale=tin=%s:pin=bt2020:min=bt2020nc:t=linear:npl=100," % tin
            + "format=gbrpf32le,"
            + "zscale=p=bt709,"
            + "tonemap=tonemap=%s:desat=0," % algo
            + "zscale=t=bt709:m=bt709:r=tv,"
            + "format=yuv420p"
        )
    return prefix + "tonemap=%s:desat=0,format=yuv420p" % algo


def frame_vf(hdr, caps, transfer=None, tail="scale=iw*sar:ih"):
    """Full -vf for one still. SDR keeps the tail (SAR scale, or subs plus scale)."""
    tail = tail or ""
    if not hdr:
        return tail
    chain = sdr_tonemap_vf(caps, preset="quality", transfer=transfer)
    if not tail:
        return chain
    return chain + "," + tail


def tonemap_input_args(hdr, caps):
    """Global ffmpeg args that belong before -i. Empty unless libplacebo is in use."""
    if hdr and (caps or {}).get("placebo"):
        return ["-init_hw_device", "vulkan"]
    return []


def build_extract_args(
    src,
    timestamp,
    dest,
    hdr=False,
    caps=None,
    transfer=None,
    tail="scale=iw*sar:ih",
):
    """ffmpeg argv for a single PNG frame. hdr selects the tone-map chain."""
    command = ["ffmpeg"]
    command.extend(tonemap_input_args(hdr, caps))
    command.extend(
        [
            "-y",
            "-v",
            "quiet",
            "-stats",
            "-ss",
            str(timestamp),
            "-i",
            src,
            "-vf",
            frame_vf(hdr, caps, transfer=transfer, tail=tail),
            "-vframes",
            "1",
            dest,
        ]
    )
    return command


def _run(command, timeout):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def ffprobe_color(path, ffprobe="ffprobe", timeout=30):
    """Raw ffprobe JSON for the first video stream, or '' when probe fails."""
    try:
        proc = _run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=color_transfer,color_primaries,color_space:stream_side_data=side_data_type",
                "-of",
                "json",
                str(path),
            ],
            timeout,
        )
    except Exception:
        return ""
    return ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace")


def looks_hdr(path, mode=None):
    """(is_hdr, transfer) for a media file. Results are cached per path."""
    forced = _mode_forces(tonemap_mode() if mode is None else mode)
    if forced is False:
        return False, None
    if forced is True:
        return True, None
    key = str(path)
    if key in _HDR_CACHE:
        return _HDR_CACHE[key]
    result = classify_probe(ffprobe_color(path))
    _HDR_CACHE[key] = result
    return result


def _filters_text(ffmpeg="ffmpeg"):
    try:
        proc = _run([ffmpeg, "-hide_banner", "-filters"], 20)
    except Exception:
        return ""
    return ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", "replace")


def _placebo_runs(ffmpeg="ffmpeg"):
    """libplacebo is listed and a tiny Vulkan graph actually runs."""
    try:
        proc = _run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-init_hw_device",
                "vulkan",
                "-f",
                "lavfi",
                "-i",
                "color=c=gray:s=64x64:d=0.1",
                "-vf",
                "libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p",
                "-f",
                "null",
                "-",
            ],
            60,
        )
    except Exception:
        return False
    return proc.returncode == 0


def ffmpeg_caps(ffmpeg="ffmpeg", refresh=False):
    """Cached {zscale, tonemap, placebo} for this process."""
    global _CAPS_CACHE
    if _CAPS_CACHE is not None and not refresh:
        return dict(_CAPS_CACHE)
    blob = _filters_text(ffmpeg).lower()
    caps = {
        "zscale": "zscale" in blob,
        "tonemap": "tonemap" in blob,
        "placebo": "libplacebo" in blob and _placebo_runs(ffmpeg),
    }
    _CAPS_CACHE = caps
    return dict(caps)
