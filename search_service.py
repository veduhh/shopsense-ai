"""Search service for ShopSense AI.

This module combines data loading, feature engineering and scoring into a
single `search_products` function that the Flask routes can call.
"""
from __future__ import annotations

import heapq
import logging
import os
from typing import Dict, List

import pandas as pd

from data_loader import PRODUCTS_CSV, iter_product_chunks
from features import (
    auth_from_rating_value,
    categorize_from_text,
    classify_query_category,
    derive_link_from_mapping,
    extract_brand_from_name,
)
from scoring import calculate_score_breakdown, compute_max_price
from scripts.fake_review_detector import compute_fake_score

logger = logging.getLogger(__name__)
_MAX_PRICE_CACHE: Dict[str, float] = {}
_MAX_PRICE_MTIME: Dict[str, float] = {}


def _prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure expected columns exist and have the right basic types."""
    df = df.copy()

    if "category" not in df.columns:
        df["category"] = "Unknown"

    # Normalise key string columns.
    if "name" not in df.columns:
        df["name"] = ""
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df["category"] = df["category"].fillna("").astype(str).str.strip()

    # Numeric coercion for price / rating.
    for col in ("price", "rating"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA

    # Drop rows with no usable price or rating.
    df = df.dropna(subset=["price", "rating"])
    return df


def _get_cached_max_price(csv_path: str) -> float:
    """Cache max price by CSV path + mtime to avoid rescanning for each request."""
    try:
        mtime = os.path.getmtime(csv_path)
    except OSError:
        return 1.0

    cached_mtime = _MAX_PRICE_MTIME.get(csv_path)
    if cached_mtime == mtime and csv_path in _MAX_PRICE_CACHE:
        return _MAX_PRICE_CACHE[csv_path]

    max_price = compute_max_price(csv_path, chunksize=20_000)
    _MAX_PRICE_CACHE[csv_path] = max_price
    _MAX_PRICE_MTIME[csv_path] = mtime
    return max_price


def _apply_feature_engineering(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Add derived features such as category, brand, authenticity, and filters."""
    if df.empty:
        return df

    # Brand: fill missing values using the product name.
    if "brand" not in df.columns:
        df["brand"] = ""
    df["brand"] = df["brand"].fillna("")
    missing_brand_mask = df["brand"].astype(str).str.strip() == ""
    if missing_brand_mask.any():
        df.loc[missing_brand_mask, "brand"] = df.loc[missing_brand_mask, "name"].apply(
            extract_brand_from_name
        )

    # Authenticity derived from rating.
    df["authenticity"] = df["rating"].apply(auth_from_rating_value)

    # High-level category for nicer display and query control.
    df["category"] = df.apply(
        lambda row: categorize_from_text(row.get("name"), row.get("category")), axis=1
    )

    # Optional query-based category restriction (do not mix phones/headphones).
    coarse = classify_query_category(query)
    if coarse == "phones":
        df = df[df["category"] != "Headphones & Earbuds"]
    elif coarse == "headphones":
        df = df[df["category"] != "Phones"]

    return df


def _build_record(row: pd.Series, brand_data: Dict, max_price: float) -> Dict:
    """Convert a pandas row into a scored product record (single offer)."""
    rec = row.to_dict()
    rec["price"] = float(rec.get("price", 0))
    rec["rating"] = float(rec.get("rating", 0))
    rec["authenticity"] = int(rec.get("authenticity", 0))

    # Shoppable link from any known URL field.
    link_val = derive_link_from_mapping(rec)
    if link_val:
        rec["link"] = link_val

    # Fake-review score: use existing column if present, else derive from text.
    if "fake_score" in row.index and row.get("fake_score") not in (None, "", "nan"):
        try:
            rec["fake_score"] = float(row.get("fake_score"))
        except Exception:
            rec["fake_score"] = 0.0
    else:
        review_text = None
        for c in ("review_text", "reviews", "description", "review"):
            if c in row.index and row.get(c) not in (None, "", "nan"):
                review_text = row.get(c)
                break
        if review_text:
            rec["fake_score"] = compute_fake_score(str(review_text))
        else:
            rec["fake_score"] = 0.0

    breakdown = calculate_score_breakdown(rec, brand_data, max_price=max_price)
    rec["ShopSense Score"] = breakdown.get("total")
    rec["score_breakdown"] = breakdown
    return rec


def search_products(
    query: str,
    *,
    top_n: int = 20,
    csv_path: str = PRODUCTS_CSV,
    brand_data: Dict | None = None,
) -> List[Dict]:
    """Search products and return grouped offers per product model.

    Instead of returning a flat list of offers, this function groups offers
    by a stable product identifier (prefer `product_id` from APIs, otherwise
    falls back to the normalised `name`). Each group contains:

        {
            "product_model": ...,
            "category": ...,
            "best_score": ...,
            "best_offer": {...},
            "offers": [{...}, ...],
        }

    This is still streaming and scales to large datasets.
    """
    query = (query or "").strip()
    if not query:
        return []

    if brand_data is None:
        brand_data = {}

    # Map from group key -> grouped record with multiple offers.
    groups: Dict[str, Dict] = {}

    try:
        max_price = _get_cached_max_price(csv_path)

        for raw_chunk in iter_product_chunks(csv_path, chunksize=20_000):
            name_col = raw_chunk.get("name", "").astype(str)
            category_col = raw_chunk.get("category", "").astype(str)

            # Wide initial filter on name + category.
            mask = name_col.str.contains(query, case=False, na=False) | category_col.str.contains(
                query, case=False, na=False
            )
            chunk = raw_chunk[mask].copy()
            if chunk.empty:
                continue

            chunk = _prepare_frame(chunk)
            if chunk.empty:
                continue

            chunk = _apply_feature_engineering(chunk, query)
            if chunk.empty:
                continue

            for _, row in chunk.iterrows():
                try:
                    rec = _build_record(row, brand_data=brand_data, max_price=max_price)
                    score = rec.get("ShopSense Score", 0.0) or 0.0

                    # Determine a grouping key: prefer product_id from API, else name.
                    product_id = (row.get("product_id") or rec.get("product_id")) or None
                    name = rec.get("name") or row.get("name")
                    if product_id:
                        key = f"id:{product_id}"
                    elif name:
                        key = f"name:{str(name).strip().lower()}"
                    else:
                        # If we cannot determine a stable key, treat as its own group.
                        key = f"row:{id(rec)}"

                    group = groups.get(key)
                    if not group:
                        group = {
                            "product_model": name or rec.get("title") or "Unknown product",
                            "category": rec.get("category") or "",
                            "best_score": 0.0,
                            "best_offer": None,
                            "offers": [],
                        }
                        groups[key] = group

                    offer = {
                        "source": rec.get("source") or rec.get("brand") or "",
                        "price": rec.get("price"),
                        "rating": rec.get("rating"),
                        "authenticity": rec.get("authenticity"),
                        "category": rec.get("category"),
                        "fake_score": rec.get("fake_score"),
                        "ShopSense Score": score,
                        "score_breakdown": rec.get("score_breakdown"),
                        "link": rec.get("link"),
                    }
                    group["offers"].append(offer)

                    # Track best offer for this model so we can sort groups.
                    if score > group["best_score"]:
                        group["best_score"] = score
                        group["best_offer"] = offer
                except Exception:
                    logger.exception("Error scoring a row; skipping")

        # Sort groups by best_score (desc) and limit to top_n product models.
        sorted_groups = sorted(groups.values(), key=lambda g: g.get("best_score", 0.0), reverse=True)
        return sorted_groups[:top_n]
    except Exception:
        logger.exception("Unexpected error while searching products")
        return []

