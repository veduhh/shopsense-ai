"""Data loading utilities for ShopSense AI.

This module keeps all CSV / JSON access and basic cleaning in one place so the
rest of the application can focus on business logic and presentation.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Iterator, List

import pandas as pd

logger = logging.getLogger(__name__)

# Central place for dataset locations used by the app.
PRODUCTS_CSV = "products.csv"
BRAND_SCORES_JSON = "brand_scores.json"


def load_brand_data(path: str = BRAND_SCORES_JSON) -> Dict[str, Dict]:
    """Load brand credibility / ethics scores from JSON.

    Returns an empty dict if the file is missing or malformed.
    """
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("could not read %s: %s", path, exc)
        return {}


def iter_product_chunks(
    csv_path: str = PRODUCTS_CSV, *, chunksize: int = 20_000
) -> Iterator[pd.DataFrame]:
    """Stream products from CSV in reasonably sized chunks.

    This keeps memory usage low even for large Kaggle-style datasets.
    """
    try:
        for chunk in pd.read_csv(csv_path, chunksize=chunksize, dtype=str):
            # Normalise column names once per chunk.
            chunk.columns = [c.strip() for c in chunk.columns]
            yield chunk
    except FileNotFoundError:
        logger.warning("%s not found; no products available", csv_path)
        return
    except pd.errors.EmptyDataError:
        logger.warning("%s is empty; no products available", csv_path)
        return
    except Exception:
        logger.exception("Unexpected error while streaming %s", csv_path)
        return


def build_search_suggestions(
    csv_path: str = PRODUCTS_CSV, *, max_items: int = 500
) -> List[str]:
    """Return a list of distinct product names / categories for the search box.

    This streams the CSV in chunks so it works even for large datasets, and
    stops collecting once `max_items` unique terms have been found.
    """
    terms: set[str] = set()
    for chunk in iter_product_chunks(csv_path):
        # Make sure expected columns exist
        chunk = chunk.copy()
        
        if "product_name" in chunk.columns:
            if "name" not in chunk.columns:
                chunk["name"] = chunk["product_name"]
            else:
                chunk["name"] = chunk["product_name"].fillna(chunk["name"])
            
        for col in ("name", "category"):
            if col not in chunk.columns:
                chunk[col] = ""
            chunk[col] = chunk[col].fillna("").astype(str).str.strip()

        for value in list(chunk["name"]) + list(chunk["category"]):
            if not value:
                continue
            terms.add(value)
            if len(terms) >= max_items:
                break
        if len(terms) >= max_items:
            break

    return sorted(terms)
