"""Feature engineering helpers for ShopSense AI.

Small, focused functions that derive higher-level features such as categories,
brand names, authenticity buckets and shoppable links from raw inputs.
"""
from __future__ import annotations

from typing import Optional


def extract_brand_from_name(name: str) -> str:
    """Best-effort brand guess from a product name."""
    if not isinstance(name, str) or not name:
        return "Unknown"
    s = name.strip()
    low = s.lower()
    if " by " in low:
        parts = s.rsplit(" by ", 1)
        candidate = parts[-1].split(",")[0].strip()
        if candidate:
            return candidate
    first = s.split()[0]
    return first or "Unknown"


def auth_from_rating_value(rating: float) -> int:
    """Map a 0–5 rating into a 1–5 authenticity bucket."""
    try:
        r = float(rating)
    except Exception:
        return 2
    if r >= 4.5:
        return 5
    if r >= 4.0:
        return 4
    if r >= 3.0:
        return 3
    return 2


def categorize_from_text(name: str, category: str) -> str:
    """Derive a simple, user-friendly high-level category.

    Both `name` and `category` may come in as floats/NaN from pandas, so we
    always coerce to strings before lowercasing.
    """
    name = str(name or "").strip().lower()
    cat = str(category or "").strip().lower()
    text = f"{name} {cat}"

    def has_any(keywords: list[str]) -> bool:
        return any(k in text for k in keywords)

    if has_any(["phone", "iphone", "galaxy", "smartphone", "oneplus", "pixel"]):
        return "Phones"
    if has_any(
        [
            "headphone",
            "headphones",
            "earbud",
            "earbuds",
            "earphone",
            "earphones",
            "airpods",
            "buds",
            "ear pod",
            "ear bud",
        ]
    ):
        return "Headphones & Earbuds"
    if has_any(["laptop", "notebook", "macbook", "chromebook"]):
        return "Laptops"
    if has_any(["watch", "smartwatch", "fitbit", "band", "wearable"]):
        return "Watches & Wearables"
    if has_any(
        [
            "shirt",
            "t-shirt",
            "t shirt",
            "tee",
            "jeans",
            "trouser",
            "trousers",
            "pant",
            "pants",
            "dress",
            "hoodie",
            "jacket",
            "kurta",
            "saree",
            "sari",
            "skirt",
        ]
    ):
        return "Clothing"

    if cat:
        return cat.title()
    return "Other"


def classify_query_category(query: str) -> Optional[str]:
    """Return a coarse category for the search query, or None."""
    q = (query or "").strip().lower()
    if not q:
        return None

    phone_terms = {"phone", "phones", "smartphone", "smartphones", "iphone", "android"}
    headphone_terms = {
        "headphone",
        "headphones",
        "earbuds",
        "earbud",
        "earphone",
        "earphones",
        "airpods",
        "buds",
    }

    if any(t in q for t in phone_terms):
        return "phones"
    if any(t in q for t in headphone_terms):
        return "headphones"
    return None


def derive_link_from_mapping(record: dict) -> Optional[str]:
    """Pick a reasonable shoppable link from common URL keys if present."""
    for key in ("link", "url", "product_url", "product_link", "buy_link"):
        val = record.get(key)
        if val not in (None, "", "nan"):
            return str(val)
    return None

