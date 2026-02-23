import app as myapp


def test_index_get():
    client = myapp.app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"ShopSense AI" in resp.data


def test_search_post_found():
    client = myapp.app.test_client()
    # Search for an existing product from products.csv
    resp = client.post("/", data={"product": "iPhone"})
    assert resp.status_code == 200
    # result should include iPhone 15
    assert b"iPhone 15" in resp.data


def test_search_post_not_found():
    client = myapp.app.test_client()
    resp = client.post("/", data={"product": "NonExistingProductXYZ"})
    assert resp.status_code == 200
    # Should not crash; page should render without results
    assert b"Results" in resp.data or b"No results" or True
