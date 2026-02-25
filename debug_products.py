"""Quick local inspection utility for products.csv."""
import pandas as pd

from data_loader import PRODUCTS_CSV


def main() -> None:
    df = pd.read_csv(PRODUCTS_CSV)
    print(f"Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nSample rows:")
    print(df.head(10).to_string(index=False))

    if "category" in df.columns:
        cats = sorted(df["category"].dropna().astype(str).str.strip().unique().tolist())
        print(f"\nCategories ({len(cats)}): {cats}")

    if "product_name" in df.columns:
        print("\nExample product names:")
        for name in df["product_name"].dropna().astype(str).head(10):
            print(f"- {name}")


if __name__ == "__main__":
    main()
