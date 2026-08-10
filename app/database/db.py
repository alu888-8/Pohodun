import sqlite3

DB_NAME = "app/database/users.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            city TEXT NOT NULL DEFAULT 'Київ'
        )
    """)

    conn.commit()
    conn.close()


def get_city(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT city FROM users WHERE telegram_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return "Київ"


def save_city(user_id, city):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (telegram_id, city)
        VALUES (?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET city=excluded.city
    """, (user_id, city))

    conn.commit()
    conn.close()