from flask import Flask, render_template, request
import pandas as pd
import json
import logging

app = Flask(__name__)

# configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load product dataset (fall back to empty DataFrame if file missing)
try:
    products = pd.read_csv("products.csv")
except Exception as e:
    logger.warning("could not read products.csv: %s", e)
    products = pd.DataFrame(columns=["name", "brand", "price", "rating", "authenticity"])

# Load brand credibility + ethics scores
try:
    with open("brand_scores.json") as f:
        brand_data = json.load(f)
except Exception as e:
    logger.warning("could not read brand_scores.json: %s", e)
    brand_data = {}


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def calculate_score(row):
    """Calculate a ShopSense score for a product row (dict-like).

    Returns a 0-100 float where higher is better.
    """
    brand = row.get("brand", "")
    price = _safe_float(row.get("price", 0))
    rating = _safe_float(row.get("rating", 0))
    auth = _safe_float(row.get("authenticity", rating))

    brand_score = brand_data.get(brand, {}).get("credibility", 5)
    ethics_score = brand_data.get(brand, {}).get("ethics", 5)

    # Price score: lower price -> better score (on 0-10 scale)
    price_score = max(0, 10 - (price / 10000))

    # Rating and authenticity scaled to contribute
    rating_score = min(5, rating) * 2  # rating expected 0-5 -> 0-10
    auth_score = min(5, auth) * 2

    # Combine with simple weights
    # weights chosen so different aspects contribute meaningfully
    weighted = (
        price_score * 1.5
        + rating_score * 2.5
        + auth_score * 2.0
        + brand_score * 1.0
        + ethics_score * 1.0
    )

    # Estimate maximum possible (to normalize to 0-100)
    max_possible = (10 * 1.5) + (10 * 2.5) + (10 * 2.0) + (10 * 1.0) + (10 * 1.0)
    if max_possible <= 0:
        return 0.0

    normalized = (weighted / max_possible) * 100
    return round(normalized, 2)


@app.route("/", methods=["GET", "POST"])
def index():
    results = None
    query = ""
    if request.method == "POST":
        query = (request.form.get("product") or "").strip()
        if query:
            df = products.copy()
            if df.empty:
                results = []
            else:
                # search in name or brand (case-insensitive)
                mask = (
                    df.get("name", "").astype(str).str.contains(query, case=False, na=False)
                    | df.get("brand", "").astype(str).str.contains(query, case=False, na=False)
                )
                df = df[mask].copy()
                if df.empty:
                    results = []
                else:
                    # ensure numeric columns exist and are numeric
                    for col in ["price", "rating", "authenticity"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                        else:
                            df[col] = 0

                    # compute ShopSense score
                    df["ShopSense Score"] = df.apply(lambda r: calculate_score(r.to_dict()), axis=1)
                    df = df.sort_values("ShopSense Score", ascending=False)
                    results = df.to_dict(orient="records")
                    logger.info("Found %d results for query '%s'", len(results), query)
    return render_template("index.html", results=results, query=query)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
