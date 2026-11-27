#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# License: GPL-3.0
# Original Kinobot by Vitiko <vhnz98@gmail.com>
#
# Quote search ranks cues instead of trusting the first fuzzy hit.
# Exact normalized text wins, then a contiguous phrase, then whole words.
# `#N` at the end of the quote picks the Nth match of that best tier, in file order.

import re

_OCC_RE = re.compile(r"\s*#(\d{1,3})\s*$")
_STRIP = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" + "\u201c\u201d\u2018\u2019\u00ab\u00bb\u2026\u2013\u2014\u00bf\u00a1 \t\r\n"


def split_occurrence(query):
    """`quote #2` -> (`quote`, 2). A bare `#2` is left alone (that is an index)."""
    text = str(query or "")
    match = _OCC_RE.search(text)
    if match and text[: match.start()].strip():
        return text[: match.start()].strip(), int(match.group(1))
    return text, 0


def normalize_quote(text):
    """Lowercase, collapse whitespace, and strip wrapping punctuation."""
    collapsed = re.sub(r"\s+", " ", (text or "").lower()).strip()
    return collapsed.strip(_STRIP).strip()


def _tokens(query):
    return [tok for tok in re.split(r"\s+", normalize_quote(query)) if tok]


def match_tier(query, text):
    """3 exact, 2 phrase, 1 whole words, 0 substring, or None when a token is missing."""
    tokens = _tokens(query)
    if not tokens:
        return None
    folded = (text or "").lower()
    if not folded or not all(tok in folded for tok in tokens):
        return None
    wanted = normalize_quote(query)
    if wanted and normalize_quote(text) == wanted:
        return 3
    phrase = re.compile(
        r"(?<!\w)" + r"[\W_]+".join(re.escape(tok) for tok in tokens) + r"(?!\w)"
    )
    if phrase.search(folded):
        return 2
    words = [
        re.compile(r"(?<!\w)" + re.escape(tok) + r"(?!\w)") for tok in tokens
    ]
    if all(pattern.search(folded) for pattern in words):
        return 1
    return 0


def _accepted(tier, query, text):
    """Whole-word hits and better are kept. A bare substring must be almost the same length."""
    if tier is None:
        return False
    if tier >= 1:
        return True
    return abs(len(normalize_quote(query)) - len(normalize_quote(text))) < 5


def pick_quote(query, texts):
    """Return (index, cleaned_query, error).

    index is None when nothing ranked well enough (the caller can still fuzzy-match).
    error is set when `#N` runs past the matches of the best tier.
    """
    cleaned, occ = split_occurrence(query)
    ranked = []
    for index, text in enumerate(texts or []):
        tier = match_tier(cleaned, text)
        if _accepted(tier, cleaned, text):
            ranked.append((tier, index))
    if not ranked:
        return None, cleaned, None
    best = max(item[0] for item in ranked)
    same = [index for tier, index in ranked if tier == best]
    if occ <= 1:
        return same[0], cleaned, None
    if occ > len(same):
        shown = cleaned.strip() or str(query or "").strip()
        return None, cleaned, (
            'Only %d match%s for "%s". #%d is past the end.'
            % (len(same), "" if len(same) == 1 else "es", shown, occ)
        )
    return same[occ - 1], cleaned, None
