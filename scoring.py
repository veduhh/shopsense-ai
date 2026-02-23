"""Scoring helpers for ShopSense AI.

This module contains a single function `calculate_score` that computes a
ShopSense score (0-100) for a product record. The function is written to be
easy to read for beginners and robust to missing / malformed values.
"""
from typing import Dict, Any, Optional
import pandas as pd


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def compute_max_price(csv_path: str, chunksize: int = 10000) -> float:
    """Compute the maximum `price` value in a CSV by streaming in chunks.

    Returns a positive float (defaults to 1.0 if no valid prices found).
    This function is efficient for large datasets because it reads only the
    `price` column and processes in chunks.
    """
    max_price = 0.0
    try:
        for chunk in pd.read_csv(csv_path, usecols=["price"], chunksize=chunksize, dtype=str):
            if "price" not in chunk.columns:
                continue
            nums = pd.to_numeric(chunk["price"], errors="coerce")
            if not nums.empty:
                local_max = nums.max(skipna=True)
                if pd.notna(local_max) and local_max > max_price:
                    max_price = float(local_max)
    except FileNotFoundError:
        return 1.0
    except pd.errors.EmptyDataError:
        return 1.0
    except Exception:
        return max(1.0, max_price)

    return max(1.0, float(max_price))


def calculate_score(record: Dict[str, Any], brand_data: Optional[Dict[str, Dict[str, Any]]] = None, max_price: Optional[float] = None) -> float:
    """Calculate a weighted ShopSense score on a 0-10 scale.

    Weights:
      - Rating: 30%
      - Price score (lower is better): 20% (normalized by `max_price`)
      - Brand credibility: 20% (defaults to midpoint if unknown)
      - Ethics score: 15%
      - Authenticity: 15%

    Args:
        record: product dict with `price`, `rating`, `brand`, `authenticity`.
        brand_data: optional mapping for brand credibility/ethics (0-10 scale expected).
        max_price: maximum price across dataset for normalization; if None, price
                   will be normalized against a conservative default.

    Returns:
        float score between 0 and 10.
    """
    if brand_data is None:
        brand_data = {}

    price = _safe_float(record.get("price", 0), 0.0)
    rating = _safe_float(record.get("rating", 0), 0.0)
    authenticity = _safe_float(record.get("authenticity", 0), 0.0)

    # Brand-level signals (expected 0-10); default to midpoint 5
    brand = record.get("brand", "") or ""
    brand_score = _safe_float(brand_data.get(brand, {}).get("credibility", 5), 5)
    ethics_score = _safe_float(brand_data.get(brand, {}).get("ethics", 5), 5)

    # Rating expected 0-5; scale to 0-10
    rating_score = max(0.0, min(5.0, rating)) / 5.0 * 10.0

    # Price score: lower price is better. Normalize by max_price to 0-10.
    if max_price is None or not isinstance(max_price, (int, float)) or max_price <= 0:
        max_price = 1.0
    # Clamp price to [0, max_price]
    price_clamped = max(0.0, min(price, max_price))
    price_score = (1.0 - (price_clamped / max_price)) * 10.0

    # Authenticity expected 1-5; scale to 0-10
    auth_score = max(0.0, min(5.0, authenticity)) / 5.0 * 10.0

    # Combine with weights (sum to 1)
    # Combine with weights to compute final score on 0-10 scale
    w_rating = 0.30
    w_price = 0.20
    w_brand = 0.20
    w_ethics = 0.15
    w_auth = 0.15

    # Component contributions (on 0-10 scale)
    contrib_rating = rating_score * w_rating
    contrib_price = price_score * w_price
    contrib_brand = brand_score * w_brand
    contrib_ethics = ethics_score * w_ethics
    contrib_auth = auth_score * w_auth

    final = contrib_rating + contrib_price + contrib_brand + contrib_ethics + contrib_auth

    # Ensure numeric result and clamp to 0-10
    try:
        final = float(final)
    except Exception:
        final = 0.0

    final = max(0.0, min(10.0, final))
    return round(final, 3)


def calculate_score_breakdown(record: Dict[str, Any], brand_data: Optional[Dict[str, Dict[str, Any]]] = None, max_price: Optional[float] = None) -> Dict[str, Any]:
    """Return component-wise breakdown and total score.

    Returns a dict with keys: `rating`, `price`, `brand`, `ethics`, `authenticity`, and `total`.
    Each component is on the 0-10 scale and `total` is the final weighted sum (0-10).
    """
    if brand_data is None:
        brand_data = {}

    price = _safe_float(record.get("price", 0), 0.0)
    rating = _safe_float(record.get("rating", 0), 0.0)
    authenticity = _safe_float(record.get("authenticity", 0), 0.0)

    brand = record.get("brand", "") or ""
    brand_score = _safe_float(brand_data.get(brand, {}).get("credibility", 5), 5)
    ethics_score = _safe_float(brand_data.get(brand, {}).get("ethics", 5), 5)

    rating_score = max(0.0, min(5.0, rating)) / 5.0 * 10.0

    if max_price is None or not isinstance(max_price, (int, float)) or max_price <= 0:
        max_price = 1.0
    price_clamped = max(0.0, min(price, max_price))
    price_score = (1.0 - (price_clamped / max_price)) * 10.0

    auth_score = max(0.0, min(5.0, authenticity)) / 5.0 * 10.0

    # weights
    w_rating = 0.30
    w_price = 0.20
    w_brand = 0.20
    w_ethics = 0.15
    w_auth = 0.15

    contrib_rating = round(rating_score * w_rating, 3)
    contrib_price = round(price_score * w_price, 3)
    contrib_brand = round(brand_score * w_brand, 3)
    contrib_ethics = round(ethics_score * w_ethics, 3)
    contrib_auth = round(auth_score * w_auth, 3)

    total = contrib_rating + contrib_price + contrib_brand + contrib_ethics + contrib_auth
    total = round(max(0.0, min(10.0, total)), 3)

    return {
        "rating": contrib_rating,
        "price": contrib_price,
        "brand": contrib_brand,
        "ethics": contrib_ethics,
        "authenticity": contrib_auth,
        "total": total,
    }
