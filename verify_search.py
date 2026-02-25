"""Sanity-check script for search results."""
from search_service import search_products


def check_query(query: str) -> None:
    results = search_products(query, top_n=5)
    print(f"\nQuery: {query!r}")
    print(f"Result groups: {len(results)}")
    if not results:
        return

    top = results[0]
    best_offer = top.get("best_offer") or {}
    print(f"Top model: {top.get('product_model')}")
    print(f"Top score: {top.get('best_score')}")
    print(f"Best source: {best_offer.get('source')}")
    print(f"Best price: {best_offer.get('price')}")


def main() -> None:
    for q in ("sneakers", "headphones", "airflex", "watch"):
        check_query(q)


if __name__ == "__main__":
    main()
