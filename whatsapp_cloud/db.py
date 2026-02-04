"""
Database layer for WhatsApp Cloud API bot (SQLite).
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "bot.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price_rs INTEGER NOT NULL,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                customer_phone TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(restaurant_id, customer_phone)
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
        """)
        # Ensure restaurant 1 exists and always use Pakistani Fast Food menu (fixes old menu on redeploy)
        conn.execute("INSERT OR IGNORE INTO restaurants (id, name) VALUES (1, 'Pakistani Fast Food')")
        conn.execute("UPDATE restaurants SET name = 'Pakistani Fast Food' WHERE id = 1")
        conn.execute("DELETE FROM menu_items WHERE restaurant_id = 1")
        pakistani_menu = [
            ("Zinger Burger", 350), ("Beef Burger", 320), ("Chicken Burger", 280),
            ("Chicken Shawarma", 250), ("Beef Shawarma", 280), ("Chicken Roll", 200),
            ("Beef Roll", 220), ("Paratha Roll", 180), ("French Fries", 120),
            ("Cheese Fries", 150), ("Chicken Tikka", 400), ("Seekh Kebab (6 pcs)", 350),
            ("Chicken Nuggets (6 pcs)", 180), ("Pepsi", 80), ("Coke", 80), ("Water", 50),
            ("Lassi", 120), ("Chai", 60),
        ]
        for name, price in pakistani_menu:
            conn.execute(
                "INSERT INTO menu_items (restaurant_id, name, price_rs) VALUES (1, ?, ?)",
                (name, price),
            )


def get_or_create_conversation(restaurant_id: int, customer_phone: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT id FROM conversations WHERE restaurant_id = ? AND customer_phone = ?",
            (restaurant_id, customer_phone),
        )
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO conversations (restaurant_id, customer_phone) VALUES (?, ?)",
            (restaurant_id, customer_phone),
        )
        return cur.lastrowid


def save_message(conversation_id: int, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )


def get_conversation_history(conversation_id: int, last_n: int = 20) -> list[dict]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
            (conversation_id, last_n),
        )
        rows = cur.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_menu_text(restaurant_id: int) -> str:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT name, price_rs FROM menu_items WHERE restaurant_id = ? ORDER BY name",
            (restaurant_id,),
        )
        rows = cur.fetchall()
    if not rows:
        return "No menu items yet."
    return "\n".join(f"- {r['name']}: Rs.{r['price_rs']}" for r in rows)
