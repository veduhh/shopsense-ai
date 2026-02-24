"""Fetch products from Google Shopping via a SERP API-style endpoint.

This script is designed for endpoints like:
  /search?engine=google_shopping

It:
  - Calls the API for a set of keywords
  - Normalises the response into a simple CSV (google_products_raw.csv)
  - That CSV can then be fed into `scripts/prepare_dataset.py` to become `products.csv`

IMPORTANT:
  - Do NOT hard-code your real API key in this file.
  - Set it as an environment variable instead, e.g. in PowerShell:

        $env:SERPAPI_KEY = "YOUR_REAL_KEY_HERE"
        python scripts\\fetch_google_shopping.py
"""
from __future__ import annotations

import csv
import os
from typing import Any, Dict, List

import requests


# Base URL for the API (adjust if your provider is different)
# For SerpApi, this is typically: https://serpapi.com/search.json
BASE_URL = os.environ.get("GOOGLE_SHOPPING_BASE_URL", "https://serpapi.com/search.json")

# API key is read from an env var for safety.
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

# Keywords to seed the dataset with. You can extend this list freely.
KEYWORDS: List[str] = [
    "iphone",
    "android phone",
    "headphones",
    "bluetooth headphones",
    "smartwatch",
    "fitness band",
    "laptop",
    "gaming laptop",
    "jacket",
    "hoodie",
]


def _fetch_shopping_results(query: str, num: int = 20) -> List[Dict[str, Any]]:
    """Call the google_shopping engine and return the raw product list.

    This assumes a SerpApi-style interface. If you use a different provider,
    adjust the params / JSON field names accordingly.
    """
    if not SERPAPI_KEY:
        raise RuntimeError("SERPAPI_KEY environment variable is not set")

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # SerpApi returns shopping results under `shopping_results`
    products = data.get("shopping_results") or []
    return products


def _row_from_product(p: Dict[str, Any]) -> Dict[str, Any]:
    """Map a Google Shopping product JSON object into a flat row."""
    title = p.get("title") or p.get("name")
    source = p.get("source") or ""
    price_str = p.get("price") or p.get("extracted_price")
    rating = p.get("rating") or p.get("reviews")  # fallback if rating missing
    category = p.get("category") or ""
    product_url = p.get("link") or p.get("product_link") or ""

    # Some SERP APIs include `product_id` or similar. Use it if present.
    product_id = p.get("product_id") or p.get("position")

    return {
        "name": title,
        "brand": source,
        "price": price_str,
        "rating": rating,
        "category": category,
        "product_url": product_url,
        # Optional: some providers include snippets / descriptions
        "review_text": p.get("snippet") or "",
        "id": product_id,
    }


def main() -> None:
    out_path = "google_products_raw.csv"
    fieldnames = [
        "id",
        "name",
        "brand",
        "price",
        "rating",
        "category",
        "product_url",
        "review_text",
    ]

    seen = set()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for kw in KEYWORDS:
            products = _fetch_shopping_results(kw, num=20)
            for p in products:
                row = _row_from_product(p)
                key = (row.get("id"), row.get("name"), row.get("product_url"))
                if key in seen:
                    continue
                seen.add(key)
                writer.writerow(row)

    print(f"Wrote raw Google Shopping products to {out_path}")
    print("Next step:")
    print("  python scripts/prepare_dataset.py --file google_products_raw.csv --out products.csv")


if __name__ == "__main__":
    main()

