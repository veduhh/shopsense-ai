"""Heuristic fake-review detector.

Lightweight, fast rules-based detector that scores review text on a 0-1
`fake_score` where 0.0 is very likely genuine and 1.0 is very likely fake.

This is intentionally simple and fast — good for streaming large datasets and
as a first-pass signal to penalize likely fake reviews in the scoring pipeline.
"""
from __future__ import annotations

import math
import re
from typing import Optional


PROMO_WORDS = {"buy", "discount", "cheap", "sale", "promo", "free", "offer", "limited", "deal"}


def _word_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower())]


def compute_fake_score(text: Optional[str]) -> float:
    """Return a heuristic fake-score in [0.0, 1.0] for `text`.

    Rules:
    - Very short reviews (<=20 chars) score higher.
    - Many exclamation marks increase suspicion.
    - Presence of URLs increases suspicion.
    - Heavy use of promotional words increases suspicion.
    - Repetitive single-word reviews increase suspicion.
    - Very high uppercase ratio increases suspicion.
    """
    if not text:
        return 0.0

    s = str(text).strip()
    if not s:
        return 0.0

    words = _word_tokens(s)
    n_words = len(words)
    n_chars = len(s)

    # Shortness: shorter is slightly more suspicious
    short_score = 0.0
    if n_chars <= 10:
        short_score = 1.0
    elif n_chars <= 40:
        short_score = (40 - n_chars) / 30.0

    # Exclamation intensity
    exclaims = s.count("!")
    exclaim_score = min(1.0, exclaims / 5.0)

    # URL presence
    url_score = 1.0 if ("http" in s.lower() or "www." in s.lower()) else 0.0

    # Promo words
    promo_count = sum(1 for w in words if w in PROMO_WORDS)
    promo_score = min(1.0, promo_count / 3.0)

    # Repetition: if a single token dominates
    rep_score = 0.0
    if n_words > 0:
        freqs = {}
        for w in words:
            freqs[w] = freqs.get(w, 0) + 1
        max_freq = max(freqs.values())
        rep_ratio = max_freq / n_words
        if rep_ratio > 0.6:
            rep_score = min(1.0, (rep_ratio - 0.6) / 0.4)

    # Uppercase ratio among letters
    letters = [c for c in s if c.isalpha()]
    upper_ratio = (sum(1 for c in letters if c.isupper()) / max(1, len(letters))) if letters else 0.0
    upper_score = min(1.0, upper_ratio / 0.4)

    # Weighted combination
    w_short = 0.20
    w_exclaim = 0.15
    w_url = 0.15
    w_promo = 0.20
    w_rep = 0.15
    w_upper = 0.15

    raw = (
        short_score * w_short
        + exclaim_score * w_exclaim
        + url_score * w_url
        + promo_score * w_promo
        + rep_score * w_rep
        + upper_score * w_upper
    )

    # Smooth and clamp
    score = max(0.0, min(1.0, raw))
    # small non-linear boost for extreme cases
    if score > 0.8:
        score = min(1.0, 0.9 + (score - 0.8) * 0.5)

    return round(score, 3)


def add_fake_score_column(df, text_col: str = "review_text", out_col: str = "fake_score"):
    """Add or overwrite a `out_col` on `df` containing the fake score.

    Works in-place and returns the DataFrame for convenience.
    """
    df[out_col] = df[text_col].fillna("").astype(str).apply(compute_fake_score)
    return df


__all__ = ["compute_fake_score", "add_fake_score_column"]
