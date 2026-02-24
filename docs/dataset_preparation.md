# Dataset preparation

Use the helper scripts in `scripts/` to download and normalize a products CSV and keep `brand_scores.json` in sync.

1) Install the extra dependency for downloads:

```powershell
python -m pip install requests
```

2) Download and normalize a remote CSV into `products.csv`:

```powershell
python scripts/prepare_dataset.py --url https://example.com/dataset.csv --out products.csv
```

3) Or normalize a local CSV:

```powershell
python scripts/prepare_dataset.py --file raw.csv --out products.csv
```

4) Update `brand_scores.json` explicitly (the prepare script will attempt this automatically if the file exists):

```powershell
python scripts/update_brand_scores.py --products products.csv --brand-scores brand_scores.json
```

Notes
- The scripts map common column names to the project's expected schema (`name`, `brand`, `price`, `rating`, `authenticity`, `category`).
- They perform conservative cleaning: strip currency symbols, coerce ratings, and attempt simple brand extraction from product names.
- Always inspect the generated `products.csv` before using it in production.
