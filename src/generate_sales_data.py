"""Generate messy raw sales data for the fake Duka Fresh chain.

All data is SYNTHETIC. Problems are planted on purpose so the pipeline
we build later has realistic things to detect and fix.
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(7)  # same output every run
RAW = Path("data/raw")

stores = list(pd.read_csv(RAW / "stores.csv").itertuples(index=False))
products = pd.read_csv(RAW / "products.csv")
customers = pd.read_csv(RAW / "customers.csv")

# Busier branches get more receipts
store_weight = {1: 1.3, 2: 1.1, 3: 1.0, 4: 0.8, 5: 0.75}

product_ids = products["product_id"].tolist()
price_of = {int(p): float(u) for p, u in zip(products["product_id"], products["unit_price"])}
product_weights = [random.uniform(0.5, 3.0) for _ in product_ids]  # some sell more
customer_ids = customers["customer_id"].tolist()

payment_names = ["M-Pesa", "Cash", "Card"]
payment_weights = [0.60, 0.28, 0.12]

START, END = date(2025, 1, 1), date(2025, 12, 31)

# ---------- 1. Build clean sales ----------
rows = []
receipt_no = 0
day = START
while day <= END:
    factor = 1.0
    if day.weekday() >= 5:   # Saturday and Sunday
        factor *= 1.25
    if day.month == 12:      # December rush
        factor *= 1.4
    if day.day >= 25:        # month-end shopping
        factor *= 1.2

    for s in stores:
        base = 25 * store_weight[s.store_id] * factor
        n_receipts = max(5, int(random.gauss(base, base * 0.15)))

        for _ in range(n_receipts):
            receipt_no += 1
            receipt_id = f"R{receipt_no:07d}"
            customer_id = random.choice(customer_ids) if random.random() < 0.65 else None
            payment = random.choices(payment_names, payment_weights)[0]
            n_lines = random.choices([1, 2, 3, 4, 5, 6],
                                     [0.20, 0.25, 0.25, 0.15, 0.10, 0.05])[0]

            line_products = set()
            while len(line_products) < n_lines:
                line_products.add(random.choices(product_ids, product_weights)[0])

            for line_no, pid in enumerate(sorted(line_products), start=1):
                quantity = random.choices([1, 2, 3, 4], [0.60, 0.25, 0.10, 0.05])[0]
                unit_price = price_of[int(pid)]
                discount = 0.0
                if random.random() < 0.10:  # 10% of lines get a discount
                    discount = round(unit_price * quantity * random.choice([0.05, 0.10]), 2)

                rows.append({
                    "receipt_id": receipt_id,
                    "line_no": line_no,
                    "sale_date": day,
                    "store_name": s.store_name,
                    "product_id": int(pid),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                    "customer_id": customer_id,
                    "payment_method": payment,
                })
    day += timedelta(days=1)

df = pd.DataFrame(rows)
df["customer_id"] = df["customer_id"].astype("Int64")  # keeps IDs as whole numbers
df["sale_date"] = df["sale_date"].astype(str)          # dates as text, like a real file
clean_rows = len(df)

# ---------- 2. Plant the problems ----------
issues = {"clean_rows_before_damage": clean_rows}

# Missing unit prices (1%)
idx = df.sample(frac=0.01, random_state=2).index
df.loc[idx, "unit_price"] = None
issues["missing_unit_price"] = len(idx)

# Negative quantities (0.5%)
idx = df.sample(frac=0.005, random_state=3).index
df.loc[idx, "quantity"] = df.loc[idx, "quantity"] * -1
issues["negative_quantity"] = len(idx)

# Misspelled store names (2%)
typos = {
    "Duka Fresh Westlands": ["Duka Fresh Westlnds", "DUKA FRESH WESTLANDS"],
    "Duka Fresh Kilimani": ["Duka Fresh Kilimani ", "duka fresh kilimani"],
    "Duka Fresh Nyali": ["Duka Fresh Nyalli", "DUKA FRESH NYALI"],
    "Duka Fresh Milimani": ["Duka Fresh Milimani.", "Duka Fresh Millimani"],
    "Duka Fresh Nakuru Town": ["Duka Fresh Nakuru", "DUKA FRESH NAKURU TOWN"],
}
idx = df.sample(frac=0.02, random_state=4).index
df.loc[idx, "store_name"] = df.loc[idx, "store_name"].apply(lambda s: random.choice(typos[s]))
issues["misspelled_store_name"] = len(idx)

# Dates in day/month/year format (3%)
idx = df.sample(frac=0.03, random_state=5).index
df.loc[idx, "sale_date"] = pd.to_datetime(df.loc[idx, "sale_date"]).dt.strftime("%d/%m/%Y")
issues["different_date_format"] = len(idx)

# Payment labels written differently (4%)
variants = {
    "M-Pesa": ["MPESA", "mpesa", "M-pesa"],
    "Cash": ["cash", "CASH"],
    "Card": ["card", "CARD", "Visa"],
}
idx = df.sample(frac=0.04, random_state=6).index
df.loc[idx, "payment_method"] = df.loc[idx, "payment_method"].apply(lambda p: random.choice(variants[p]))
issues["inconsistent_payment_label"] = len(idx)

# Duplicate rows (1%): exact copies added back in
dups = df.sample(frac=0.01, random_state=1)
issues["duplicate_rows_added"] = len(dups)
df = pd.concat([df, dups])
df = df.sort_values(["receipt_id", "line_no"], kind="stable").reset_index(drop=True)

# ---------- 3. Save ----------
df.to_csv(RAW / "sales_raw.csv", index=False)            # full file (too big for GitHub)
df.head(300).to_csv(RAW / "sales_sample.csv", index=False)  # small sample for GitHub
with open(RAW / "planted_issues.json", "w") as f:
    json.dump(issues, f, indent=2)

print(f"Created {len(df):,} sales lines across {receipt_no:,} receipts.")
print("Planted problems:", issues)