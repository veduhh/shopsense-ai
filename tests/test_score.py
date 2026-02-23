from scoring import calculate_score, compute_max_price


def test_calculate_score_basic():
    # High-quality product should return a positive score within 0-10
    brand_data = {"Acme": {"credibility": 9, "ethics": 8}}
    row = {"brand": "Acme", "price": 1000, "rating": 4.5, "authenticity": 5}
    max_price = compute_max_price("products.csv", chunksize=1000)
    score = calculate_score(row, brand_data, max_price=max_price)
    assert isinstance(score, float)
    assert 0 <= score <= 10
    assert score > 5


def test_calculate_score_missing_fields():
    # Missing numeric fields should not crash and return bounded score (0-10)
    row = {"brand": "Unknown"}
    max_price = compute_max_price("products.csv", chunksize=1000)
    score = calculate_score(row, {}, max_price=max_price)
    assert isinstance(score, float)
    assert 0 <= score <= 10


def test_price_affects_score():
    # Lower price should generally yield a better (higher) score
    brand_data = {}
    base = {"brand": "X", "rating": 4, "authenticity": 4}
    low_price = dict(base, price=100)
    high_price = dict(base, price=10000)
    max_price = compute_max_price("products.csv", chunksize=1000)
    s_low = calculate_score(low_price, brand_data, max_price=max_price)
    s_high = calculate_score(high_price, brand_data, max_price=max_price)
    assert s_low >= s_high
