import csv

import app as myapp


def _first_product_name_from_csv(path: str = "products.csv") -> str:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("product_name") or row.get("name") or "").strip()
            if name:
                return name
    raise AssertionError("No product_name/name rows found in products.csv")


def test_index_get():
    client = myapp.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ShopSense AI" in resp.data


def test_search_post_found():
    client = myapp.app.test_client()
    # Search using real dataset content so this test stays valid if CSV changes.
    full_name = _first_product_name_from_csv()
    query = full_name.split()[0]
    resp = client.post("/", data={"product": query})
    assert resp.status_code == 200
    assert full_name.encode("utf-8") in resp.data


def test_search_post_not_found():
    client = myapp.app.test_client()
    resp = client.post("/", data={"product": "NonExistingProductXYZ"})
    assert resp.status_code == 200
    # Should not crash; page should render without results
    assert b"No results found" in resp.data


def test_health():
    client = myapp.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.is_json
    assert resp.get_json().get("status") == "ok"
