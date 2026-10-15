"""Generate clean reference data for the fake Duka Fresh supermarket chain.

All data here is SYNTHETIC (made up). Prices are illustrative, not real.
"""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

random.seed(42)  # same "random" results every time we run it

OUT_DIR = Path("data/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- Stores (the 5 branches) ----
stores = [
    (1, "Duka Fresh Westlands", "Nairobi", "Nairobi"),
    (2, "Duka Fresh Kilimani", "Nairobi", "Nairobi"),
    (3, "Duka Fresh Nyali", "Mombasa", "Coast"),
    (4, "Duka Fresh Milimani", "Kisumu", "Nyanza"),
    (5, "Duka Fresh Nakuru Town", "Nakuru", "Rift Valley"),
]
pd.DataFrame(
    stores, columns=["store_id", "store_name", "town", "region"]
).to_csv(OUT_DIR / "stores.csv", index=False)

# ---- Products (id, name, category, cost price, selling price in KES) ----
products = [
    (1, "Maize Flour 2kg", "Staples", 150, 190),
    (2, "Sugar 1kg", "Staples", 140, 170),
    (3, "Rice 2kg", "Staples", 300, 380),
    (4, "Cooking Oil 1L", "Staples", 260, 330),
    (5, "Wheat Flour 2kg", "Staples", 170, 215),
    (6, "Fresh Milk 500ml", "Dairy & Bakery", 55, 70),
    (7, "Bread 400g", "Dairy & Bakery", 50, 65),
    (8, "Eggs Tray of 30", "Dairy & Bakery", 400, 480),
    (9, "Yoghurt 500ml", "Dairy & Bakery", 85, 110),
    (10, "Tomatoes 1kg", "Fresh Produce", 60, 90),
    (11, "Onions 1kg", "Fresh Produce", 70, 100),
    (12, "Sukuma Wiki Bunch", "Fresh Produce", 10, 20),
    (13, "Bananas 1kg", "Fresh Produce", 70, 100),
    (14, "Bar Soap", "Household", 45, 65),
    (15, "Toothpaste 100ml", "Household", 120, 160),
    (16, "Toilet Paper 4 Pack", "Household", 150, 200),
    (17, "Laundry Detergent 1kg", "Household", 230, 290),
    (18, "Soda 500ml", "Beverages", 45, 60),
    (19, "Bottled Water 1L", "Beverages", 30, 50),
    (20, "Tea Leaves 250g", "Beverages", 110, 140),
]
pd.DataFrame(
    products,
    columns=["product_id", "product_name", "category", "cost_price", "unit_price"],
).to_csv(OUT_DIR / "products.csv", index=False)

# ---- Customers (300 made-up people) ----
first_names = ["Wanjiku", "Otieno", "Achieng", "Kamau", "Mwangi", "Njeri",
               "Omondi", "Akinyi", "Kiptoo", "Chebet", "Mutua", "Wambui",
               "Hassan", "Fatuma", "Odhiambo", "Nyambura"]
last_names = ["Kariuki", "Ochieng", "Kimani", "Mutiso", "Wekesa", "Rotich",
              "Njoroge", "Adhiambo", "Kibet", "Juma", "Maina", "Owino"]

customers = []
for customer_id in range(1, 301):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    join_date = date(2024, 1, 1) + timedelta(days=random.randint(0, 364))
    customers.append((customer_id, name, join_date.isoformat()))
pd.DataFrame(
    customers, columns=["customer_id", "customer_name", "join_date"]
).to_csv(OUT_DIR / "customers.csv", index=False)

# ---- Payment methods ----
payment_methods = [(1, "M-Pesa"), (2, "Cash"), (3, "Card")]
pd.DataFrame(
    payment_methods, columns=["payment_id", "method_name"]
).to_csv(OUT_DIR / "payment_methods.csv", index=False)

print(f"Created {len(stores)} stores, {len(products)} products, "
      f"{len(customers)} customers, {len(payment_methods)} payment methods.")