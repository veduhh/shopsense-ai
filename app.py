from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import logging
import heapq
from scoring import calculate_score, compute_max_price, calculate_score_breakdown

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
            results = search_products(query, top_n=10)

    return render_template("index.html", results=results, query=query)


def search_products(query: str, top_n: int = 10):
    """Search products by name or category and return top-N scored results.

    Streams `PRODUCTS_CSV` to handle large datasets efficiently.
    """
    heap = []
    try:
        max_price = compute_max_price(PRODUCTS_CSV, chunksize=10000)
        for chunk in pd.read_csv(PRODUCTS_CSV, chunksize=10000, dtype=str):
            chunk.columns = [c.strip() for c in chunk.columns]
            if "category" not in chunk.columns:
                chunk["category"] = "Unknown"

            name_col = chunk.get("name", "")
            category_col = chunk.get("category", "")
            mask = (
                name_col.astype(str).str.contains(query, case=False, na=False)
                | category_col.astype(str).str.contains(query, case=False, na=False)
            )
            filtered = chunk[mask].copy()
            if filtered.empty:
                continue

            filtered["name"] = filtered.get("name", "").astype(str).str.strip()
            filtered["category"] = filtered.get("category", "").astype(str).str.strip()
            filtered = filtered[(filtered["name"] != "") | (filtered["category"] != "")]

            for col in ["price", "rating"]:
                if col in filtered.columns:
                    filtered[col] = pd.to_numeric(filtered[col], errors="coerce")
                else:
                    filtered[col] = pd.NA

            filtered = filtered.dropna(subset=["price", "rating"]) 
            if filtered.empty:
                continue

            def _extract_brand(name: str) -> str:
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
                return first

            if "brand" not in filtered.columns:
                filtered["brand"] = ""
            filtered["brand"] = filtered["brand"].fillna("")
            missing_brand_mask = filtered["brand"].astype(str).str.strip() == ""
            if missing_brand_mask.any():
                filtered.loc[missing_brand_mask, "brand"] = (
                    filtered.loc[missing_brand_mask, "name"].apply(_extract_brand)
                )

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

            for _, row in filtered.iterrows():
                try:
                    rec = row.to_dict()
                    rec["price"] = float(rec.get("price", 0))
                    rec["rating"] = float(rec.get("rating", 0))
                    rec["authenticity"] = int(rec.get("authenticity", 0))
                    breakdown = calculate_score_breakdown(rec, brand_data, max_price=max_price)
                    rec["ShopSense Score"] = breakdown.get("total")
                    rec["score_breakdown"] = breakdown
                    score = rec["ShopSense Score"]
                    if len(heap) < top_n:
                        heapq.heappush(heap, (score, rec))
                    else:
                        if score > heap[0][0]:
                            heapq.heapreplace(heap, (score, rec))
                except Exception:
                    logger.exception("Error scoring a row; skipping")

        results = [item[1] for item in sorted(heap, key=lambda x: x[0], reverse=True)]
        return results
    except FileNotFoundError:
        logger.warning("products.csv not found; returning no results")
        return []
    except pd.errors.EmptyDataError:
        logger.warning("products.csv is empty")
        return []
    except Exception:
        logger.exception("Unexpected error while searching products")
        return []


@app.route('/api/search', methods=['GET'])
def api_search():
    """Simple JSON API to search products. Query param: `product`.

    Returns JSON with `query` and `results` (same records the UI shows).
    """
    q = (request.args.get('product') or '').strip()
    if not q:
        return jsonify({'error': 'missing "product" query parameter', 'results': []}), 400
    results = search_products(q, top_n=10)
    return jsonify({'query': q, 'results': results})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
