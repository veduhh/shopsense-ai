from flask import Flask, render_template, request
import pandas as pd
import json
import logging
import heapq
from scoring import calculate_score

app = Flask(__name__)

# configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRODUCTS_CSV = "products.csv"

# We stream `products.csv` in chunks when searching to support large files.
# Keep a small in-memory cache for quick lookups if desired.

# Load brand credibility + ethics scores
try:
    with open("brand_scores.json") as f:
        brand_data = json.load(f)
except Exception as e:
    logger.warning("could not read brand_scores.json: %s", e)
    brand_data = {}


# The scoring implementation lives in `scoring.py` and is imported above.


@app.route("/", methods=["GET", "POST"])
def index():
    """Home page: simple form to search products and return scored results.

    This uses streaming reads of `products.csv` so the app can handle
    large datasets without loading everything into memory at once.
    """
    results = []
    query = ""
    if request.method == "POST":
        query = (request.form.get("product") or "").strip()
        if query:
            # We'll keep only the top N results in a min-heap to bound memory.
            top_n = 50
            heap = []  # min-heap of (score, record)

            try:
                for chunk in pd.read_csv(PRODUCTS_CSV, chunksize=10000, dtype=str):
                    # Build a boolean mask searching `name` and `brand` safely.
                    name_col = chunk.get("name", "")
                    brand_col = chunk.get("brand", "")
                    mask = (
                        name_col.astype(str).str.contains(query, case=False, na=False)
                        | brand_col.astype(str).str.contains(query, case=False, na=False)
                    )
                    filtered = chunk[mask].copy()
                    if filtered.empty:
                        continue

                    # Ensure numeric columns exist and are numeric with safe defaults
                    for col in ["price", "rating", "authenticity"]:
                        if col in filtered.columns:
                            filtered[col] = pd.to_numeric(filtered[col], errors="coerce").fillna(0)
                        else:
                            filtered[col] = 0

                    # Compute scores using the imported `calculate_score`.
                    for _, row in filtered.iterrows():
                        try:
                            rec = row.to_dict()
                            score = calculate_score(rec, brand_data)
                            rec["ShopSense Score"] = score
                            # Use negative score for max-heap behavior on min-heap
                            if len(heap) < top_n:
                                heapq.heappush(heap, (score, rec))
                            else:
                                # Replace smallest if current is better
                                if score > heap[0][0]:
                                    heapq.heapreplace(heap, (score, rec))
                        except Exception:
                            # Skip individual problematic rows but keep running
                            logger.exception("Error scoring a row; skipping")
                # Extract heap contents sorted descending
                results = [item[1] for item in sorted(heap, key=lambda x: x[0], reverse=True)]
                logger.info("Found %d results for query '%s'", len(results), query)
            except FileNotFoundError:
                logger.warning("products.csv not found; returning no results")
                results = []
            except pd.errors.EmptyDataError:
                logger.warning("products.csv is empty")
                results = []
            except Exception:
                logger.exception("Unexpected error while searching products")
                results = []

    return render_template("index.html", results=results, query=query)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
