import sqlite3


DB_NAME = "app/database/users.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Користувачі
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            city TEXT NOT NULL DEFAULT 'Київ'
        )
    """)

    # Контент дня: анекдот + побажання
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_content (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            content_date TEXT NOT NULL,
            joke TEXT NOT NULL,
            greeting TEXT NOT NULL
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

    # Якщо користувача ще немає —
    # автоматично додаємо його
    if row is None:
        cursor.execute(
            """
            INSERT INTO users (telegram_id, city)
            VALUES (?, ?)
            """,
            (user_id, "Київ")
        )

        conn.commit()
        conn.close()

        return "Київ"

    conn.close()

    return row[0]


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


def get_users_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_daily_content():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content_date, joke, greeting
        FROM daily_content
        WHERE id=1
    """)

    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "date": row[0],
            "joke": row[1],
            "greeting": row[2]
        }

    return None


def save_daily_content(content_date, joke, greeting):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_content (
            id,
            content_date,
            joke,
            greeting
        )
        VALUES (1, ?, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            content_date=excluded.content_date,
            joke=excluded.joke,
            greeting=excluded.greeting
    """, (
        content_date,
        joke,
        greeting
    ))

    conn.commit()
    conn.close()