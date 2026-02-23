"""Scoring helpers for ShopSense AI.

This module contains a single function `calculate_score` that computes a
ShopSense score (0-100) for a product record. The function is written to be
easy to read for beginners and robust to missing / malformed values.
"""
from typing import Dict, Any


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def calculate_score(record: Dict[str, Any], brand_data: Dict[str, Dict[str, Any]] = None) -> float:
    """Calculate a ShopSense score for a single product record.

    Args:
        record: a dict-like product with keys like `brand`, `price`, `rating`, `authenticity`.
        brand_data: optional mapping with brand credibility/ethics scores.

    Returns:
        float: score between 0 and 100 (higher is better).

    Notes:
    - The implementation uses a simple weighted sum of price, rating,
      authenticity, and brand attributes. It's intentionally kept simple
      so beginners can understand and adjust weights.
    - Missing numeric values are treated as 0.
    """
    if brand_data is None:
        brand_data = {}

    brand = record.get("brand", "") or ""
    price = _safe_float(record.get("price", 0), 0.0)
    rating = _safe_float(record.get("rating", 0), 0.0)
    auth = _safe_float(record.get("authenticity", rating), rating)

    # Brand-level signals (default to midpoint if unknown)
    brand_score = _safe_float(brand_data.get(brand, {}).get("credibility", 5), 5)
    ethics_score = _safe_float(brand_data.get(brand, {}).get("ethics", 5), 5)

    # Price score: lower price gets better score on 0-10 scale.
    # The divisor controls how sensitive the score is to price; adjust as needed.
    price_score = max(0.0, 10.0 - (price / 10000.0))

    # rating and authenticity are expected on a 0-5 scale; scale them to 0-10
    rating_score = min(5.0, rating) * 2.0
    auth_score = min(5.0, auth) * 2.0

    # Combine with simple weights. These can be tuned for your use case.
    weighted = (
        price_score * 1.5
        + rating_score * 2.5
        + auth_score * 2.0
        + brand_score * 1.0
        + ethics_score * 1.0
    )

    # Normalize to 0-100 range
    max_possible = (10.0 * 1.5) + (10.0 * 2.5) + (10.0 * 2.0) + (10.0 * 1.0) + (10.0 * 1.0)
    if max_possible <= 0:
        return 0.0

    normalized = (weighted / max_possible) * 100.0
    return round(float(normalized), 2)
