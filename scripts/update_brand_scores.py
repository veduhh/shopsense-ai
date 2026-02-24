"""Utilities to update `brand_scores.json` from a DataFrame of products.

The updater will add any brands missing from the JSON file with sensible
default credibility and ethics scores so the scoring pipeline can run.
"""
from __future__ import annotations

import json
from typing import Dict

import pandas as pd


def _load_json(path: str) -> Dict[str, Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_json(path: str, data: Dict[str, Dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_brand_scores_from_df(df: pd.DataFrame, json_path: str, default_score: int = 5) -> None:
    """Ensure every brand in `df` exists in `json_path`. New brands get default scores.

    The brand score entry shape is flexible, but this function will ensure a
    minimal shape: {"credibility": int, "ethics": int}
    """
    existing = _load_json(json_path)
    brands = set(df["brand"].dropna().astype(str).unique())
    updated = False
    for b in sorted(brands):
        if b not in existing:
            existing[b] = {"credibility": default_score, "ethics": default_score}
            updated = True

    if updated:
        _save_json(json_path, existing)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--products", default="products.csv", help="Products CSV to scan for brands")
    p.add_argument("--brand-scores", default="brand_scores.json", help="Brand scores JSON to update")
    args = p.parse_args()

    df = pd.read_csv(args.products)
    update_brand_scores_from_df(df, args.brand_scores)
    print(f"Updated {args.brand_scores} from {args.products}")
