"""Download and normalize a product CSV into the repository's `products.csv` format.

Usage examples:
python scripts/prepare_dataset.py --url https://example.com/dataset.csv --out products.csv
python scripts/prepare_dataset.py --file local.csv --out products.csv

This script attempts to map common column names to the expected schema:
- name, title, product_name -> name
- brand, maker, manufacturer -> brand
- price, cost -> price
- rating, stars -> rating
- authenticity, is_authentic -> authenticity

It will coerce types, extract brand heuristically when missing, and call
`scripts.update_brand_scores.update_brand_scores_from_df` to ensure new brands
exist in `brand_scores.json` with default values.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional

import pandas as pd

try:
    import requests
except Exception:  # pragma: no cover - requests may not be installed in test env
    requests = None

from scripts.update_brand_scores import update_brand_scores_from_df


COMMON_COL_MAP = {
    "title": "name",
    "product_name": "name",
    "item": "name",
    "maker": "brand",
    "manufacturer": "brand",
    "cost": "price",
    "stars": "rating",
    "is_authentic": "authenticity",
}


def download_csv(url: str, target: str) -> str:
    if requests is None:
        raise RuntimeError("requests is required to download remote files; pip install requests")
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    with open(target, "wb") as f:
        for chunk in resp.iter_content(32_768):
            if chunk:
                f.write(chunk)
    return target


def _clean_price(x: object) -> Optional[float]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    s = re.sub(r"[^0-9\.\-]", "", s)
    try:
        return float(s) if s != "" else None
    except ValueError:
        return None


def _clean_rating(x: object) -> Optional[float]:
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        # sometimes ratings like '4/5' or '4 out of 5'
        m = re.search(r"([0-9]+(\.[0-9]+)?)", str(x))
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
        return None


def _clean_authenticity(x: object) -> Optional[str]:
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    if s in ("yes", "true", "1", "y", "authentic"):
        return "authentic"
    if s in ("no", "false", "0", "n", "counterfeit"):
        return "not_authentic"
    return None


def _extract_brand_from_name(name: str) -> Optional[str]:
    if not name:
        return None
    # heuristics: first token, or leading word if capitalized
    tokens = re.split(r"[\-_/\\\s]+", name)
    if tokens:
        candidate = tokens[0].strip()
        # ignore short tokens like 'the' or 'new'
        if len(candidate) >= 2:
            return candidate
    return None


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # normalize column names
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    lower_map = {c: c.lower() for c in df.columns}
    df.rename(columns=lower_map, inplace=True)
    # apply common column name mappings
    for c in list(df.columns):
        mapped = COMMON_COL_MAP.get(c)
        if mapped and mapped not in df.columns:
            df.rename(columns={c: mapped}, inplace=True)

    # Ensure expected columns exist
    for col in ("name", "brand", "category", "price", "rating", "authenticity"):
        if col not in df.columns:
            df[col] = pd.NA

    # Coerce types
    df["price"] = df["price"].apply(_clean_price)
    df["rating"] = df["rating"].apply(_clean_rating)
    df["authenticity"] = df["authenticity"].apply(_clean_authenticity)

    # Extract brand when missing
    missing_brand = df["brand"].isna()
    if missing_brand.any():
        df.loc[missing_brand, "brand"] = df.loc[missing_brand, "name"].apply(_extract_brand_from_name)

    # Fill category with 'Uncategorized' when missing
    df["category"].fillna("Uncategorized", inplace=True)

    # Trim strings
    for c in ["name", "brand", "category"]:
        df[c] = df[c].astype(str).str.strip()

    return df


def main(argv=None):
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", help="HTTP URL to download CSV from")
    g.add_argument("--file", help="Local CSV file to read")
    p.add_argument("--out", default="products.csv", help="Output CSV path")
    p.add_argument("--brand-scores", default="brand_scores.json", help="Brand scores JSON to update")
    args = p.parse_args(argv)

    if args.url:
        if requests is None:
            print("requests not installed. Install with: pip install requests", file=sys.stderr)
            sys.exit(2)
        tmp = "__download_tmp.csv"
        print(f"Downloading {args.url} -> {tmp}")
        download_csv(args.url, tmp)
        src = tmp
    else:
        src = args.file

    if not os.path.exists(src):
        print(f"Source file not found: {src}", file=sys.stderr)
        sys.exit(2)

    # Read via pandas (let pandas infer delimiter)
    df = pd.read_csv(src, low_memory=False)
    print(f"Loaded {len(df)} rows from {src}")
    df = normalize_df(df)
    print("Normalized dataframe; sample columns:", list(df.columns)[:6])

    # Save output
    df.to_csv(args.out, index=False)
    print(f"Wrote normalized products to {args.out}")

    # Update brand scores with discovered brands
    if os.path.exists(args.brand_scores):
        update_brand_scores_from_df(df, args.brand_scores)
        print(f"Updated brand scores in {args.brand_scores}")
    else:
        print(f"Brand scores file not found: {args.brand_scores}; skipping update")


if __name__ == "__main__":
    main()
