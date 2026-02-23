import app


def test_calculate_score_basic():
    # Ensure deterministic result for a high-quality product
    app.brand_data = {"Acme": {"credibility": 9, "ethics": 8}}
    row = {"brand": "Acme", "price": 1000, "rating": 4.5, "authenticity": 5}
    score = app.calculate_score(row)
    assert isinstance(score, float)
    assert score > 0


def test_calculate_score_missing_fields():
    # Missing numeric fields should not crash
    app.brand_data = {}
    row = {"brand": "Unknown"}
    score = app.calculate_score(row)
    assert score >= 0
