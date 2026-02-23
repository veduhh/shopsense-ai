import pandas as pd

p = pd.read_csv('products.csv')
print('columns:', p.columns.tolist())
print(p)
q = 'iPhone'
mask = p.get('name','').astype(str).str.contains(q, case=False, na=False) | p.get('brand','').astype(str).str.contains(q, case=False, na=False)
print('mask sum:', mask.sum())
print(p[mask])
