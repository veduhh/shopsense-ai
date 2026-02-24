"""Run the heuristic fake-review detector over `products.csv` and write `fake_score`.

Usage:
    python scripts/run_add_fake_scores.py --in products.csv --out products.csv
"""
from __future__ import annotations

import argparse
import pandas as pd

from scripts.fake_review_detector import add_fake_score_column, compute_fake_score


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="infile", default="products.csv")
    p.add_argument("--out", dest="outfile", default="products.csv")
    args = p.parse_args(argv)

    df = pd.read_csv(args.infile, low_memory=False)
    # If there's a 'review_text' column, use it; otherwise try 'reviews' or 'description'
    text_col = None
    for candidate in ("review_text", "reviews", "description", "review"):
        if candidate in df.columns:
            text_col = candidate
            break

    if text_col is None:
        # no text column; create fake_score=0 for all rows
        df["fake_score"] = 0.0
    else:
        add_fake_score_column(df, text_col=text_col, out_col="fake_score")

    df.to_csv(args.outfile, index=False)
    print(f"Wrote fake_score to {args.outfile} (text_col={text_col})")


if __name__ == "__main__":
    main()
