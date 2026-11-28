# kinobot
![](https://tokei.rs/b1/github/vitiko98/kinobot)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=VZWSWVGZGJRMU&source=url)


Welcome to the source code of `kinobot`. This code is provided with the purpose of being reused or modified in other projects or analyzed for better understanding.

## Setup

Copy `config.example.py` to `config.py`, then fill it in. `config.py` is gitignored.

## Fork additions

This repository is a fork of [vitiko98/kinobot](https://github.com/vitiko98/kinobot) by Vitiko. The original project stays under GPL-3.0, and Vitiko's copyright in `LICENSE` is unchanged.

What this fork adds on top of that code:

- **HDR to SDR tone mapping.** Frames grabbed with ffmpeg from HDR10, HLG, or Dolby Vision sources are converted to BT.709 before the usual display-aspect scale. When ffmpeg can run `libplacebo`, that filter applies Dolby Vision. Otherwise the chain is `zscale` plus a hable tonemap (reinhard is available as the fast preset inside the helper). Set `KINOBOT_HDR_TONEMAP=off` to skip it, or `on` to always tone-map. The default is `auto`.
- **Corner zoom.** `--tl`, `--tr`, `--bl`, and `--br` (any case) zoom toward that corner. Without `--zoom-factor` the zoom is 2x. One corner per request or per bracket.
- **Caption position.** `--position TL|TR|BL|BR|TC|C|BC` places the quote. The default remains bottom centre. `--text-align left` and `right` now move the line, and a corner caption that is too wide is wrapped again so it stays on the frame.
- **Quote matching.** A bracket quote prefers an exact line (case and surrounding punctuation ignored), then the same words as a phrase, then whole words, in subtitle order. `[quote #2]` uses the second match of that best kind. A near-miss that does not share those words still falls back to the original fuzzy search.
- **Crop and aspect.** Aspect-quotient crop boxes stay inside the frame, and a ratio that cannot be reached is reported as an invalid request. Display-aspect correction uses height times the DAR (OpenCV's array shape is height, then width), so anamorphic frames are not stretched the wrong way. `--aspect-quotient` must sit between 1 and 2.5.
