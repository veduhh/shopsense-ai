from flask import Flask, render_template, request, jsonify
import logging
import os

from data_loader import load_brand_data, build_search_suggestions
from search_service import search_products

app = Flask(__name__)

# Configure simple logging for the whole app.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load brand credibility + ethics scores once at startup.
brand_data = load_brand_data()
search_suggestions = build_search_suggestions()


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
            # Show a slightly larger set of strong matches so users see more options.
            results = search_products(query, top_n=20, brand_data=brand_data)

    return render_template("index.html", results=results, query=query, suggestions=search_suggestions)

@app.route('/api/search', methods=['GET'])
def api_search():
    """Simple JSON API to search products. Query param: `product`.

    Returns JSON with `query` and `results` (same records the UI shows).
    """
    q = (request.args.get('product') or '').strip()
    if not q:
        return jsonify({'error': 'missing "product" query parameter', 'results': []}), 400
    results = search_products(q, top_n=20, brand_data=brand_data)
    return jsonify({'query': q, 'results': results})


@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint for load balancers and platform probes."""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=5000)


def create_app():
    """Application factory for WSGI servers.

    Returns the Flask `app` instance. Kept simple for compatibility with
    deployment platforms that prefer a factory function.
    """
    return app
