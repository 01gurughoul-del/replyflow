"""
Seed Pakistani fast food menu. Run once: python seed_menu.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import db

PAKISTANI_FAST_FOOD = [
    ("Zinger Burger", 350),
    ("Beef Burger", 320),
    ("Chicken Burger", 280),
    ("Chicken Shawarma", 250),
    ("Beef Shawarma", 280),
    ("Chicken Roll", 200),
    ("Beef Roll", 220),
    ("Paratha Roll", 180),
    ("French Fries", 120),
    ("Cheese Fries", 150),
    ("Chicken Tikka", 400),
    ("Seekh Kebab (6 pcs)", 350),
    ("Chicken Nuggets (6 pcs)", 180),
    ("Pepsi", 80),
    ("Coke", 80),
    ("Water", 50),
    ("Lassi", 120),
    ("Chai", 60),
]


def seed():
    db.init_db()
    with db.get_conn() as conn:
        conn.execute("UPDATE restaurants SET name = ? WHERE id = 1", ("Pakistani Fast Food",))
        conn.execute("DELETE FROM menu_items WHERE restaurant_id = 1")
        for name, price in PAKISTANI_FAST_FOOD:
            conn.execute(
                "INSERT INTO menu_items (restaurant_id, name, price_rs) VALUES (1, ?, ?)",
                (name, price),
            )
    print("Pakistani fast food menu seeded.")


if __name__ == "__main__":
    seed()
