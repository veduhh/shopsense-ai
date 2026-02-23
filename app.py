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
                    # Normalize column names and ensure expected columns exist
                    chunk.columns = [c.strip() for c in chunk.columns]

                    # If `category` is missing entirely, create a default to avoid
                    # dropping useful rows when the dataset doesn't include it.
                    if "category" not in chunk.columns:
                        chunk["category"] = "Unknown"

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

                    # Drop rows missing required textual fields (`name`, `category`).
                    filtered["name"] = filtered.get("name", "").astype(str).str.strip()
                    filtered["category"] = filtered.get("category", "").astype(str).str.strip()
                    filtered = filtered[filtered["name"] != ""]

                    # Convert numeric columns safely; coerce errors to NaN
                    for col in ["price", "rating"]:
                        if col in filtered.columns:
                            filtered[col] = pd.to_numeric(filtered[col], errors="coerce")
                        else:
                            filtered[col] = pd.NA

                    # Drop rows missing numeric values (price, rating)
                    filtered = filtered.dropna(subset=["price", "rating"]) 

                    if filtered.empty:
                        continue

                    # Extract brand automatically from `name` when missing or empty
                    def _extract_brand(name: str) -> str:
                        if not isinstance(name, str) or not name:
                            return "Unknown"
                        s = name.strip()
                        # Prefer "by" patterns: "Product by Brand"
                        low = s.lower()
                        if " by " in low:
                            # take part after the last ' by '
                            parts = s.rsplit(" by ", 1)
                            candidate = parts[-1].split(",")[0].strip()
                            if candidate:
                                return candidate
                        # Otherwise take the first token (common for 'Brand Product')
                        first = s.split()[0]
                        return first

                    if "brand" not in filtered.columns:
                        filtered["brand"] = ""
                    filtered["brand"] = filtered["brand"].fillna("")
                    # Fill missing brands using the heuristic
                    missing_brand_mask = filtered["brand"].astype(str).str.strip() == ""
                    if missing_brand_mask.any():
                        filtered.loc[missing_brand_mask, "brand"] = (
                            filtered.loc[missing_brand_mask, "name"].apply(_extract_brand)
                        )

                    # Generate `authenticity` score from `rating` using the mapping
                    def _auth_from_rating(r):
                        try:
                            r = float(r)
                        except Exception:
                            return 2
                        if r >= 4.5:
                            return 5
                        if r >= 4.0:
                            return 4
                        if r >= 3.0:
                            return 3
                        return 2

                    filtered["authenticity"] = filtered["rating"].apply(_auth_from_rating)

                    # Compute scores using the imported `calculate_score`.
                    for _, row in filtered.iterrows():
                        try:
                            rec = row.to_dict()
                            # Ensure price and rating are plain Python floats
                            rec["price"] = float(rec.get("price", 0))
                            rec["rating"] = float(rec.get("rating", 0))
                            rec["authenticity"] = int(rec.get("authenticity", 0))
                            score = calculate_score(rec, brand_data)
                            rec["ShopSense Score"] = score
                            if len(heap) < top_n:
                                heapq.heappush(heap, (score, rec))
                            else:
                                if score > heap[0][0]:
                                    heapq.heapreplace(heap, (score, rec))
                        except Exception:
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
