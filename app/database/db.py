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

    # Контент дня окремо для кожного міста
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_content_city (
            city TEXT PRIMARY KEY,
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


def get_all_users():
    """
    Повертає всіх користувачів та їхні міста.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT telegram_id, city
        FROM users
        ORDER BY telegram_id
    """)

    rows = cursor.fetchall()

    conn.close()

    users = []

    for row in rows:
        users.append({
            "telegram_id": row[0],
            "city": row[1]
        })

    return users


def get_daily_content(city):
    """
    Отримує контент дня для конкретного міста.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content_date, joke, greeting
        FROM daily_content_city
        WHERE city=?
    """, (city,))

    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "date": row[0],
            "joke": row[1],
            "greeting": row[2]
        }

    return None


def save_daily_content(city, content_date, joke, greeting):
    """
    Зберігає контент дня для конкретного міста.
    Якщо для міста вже є запис — оновлює його.
    """

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_content_city (
            city,
            content_date,
            joke,
            greeting
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(city)
        DO UPDATE SET
            content_date=excluded.content_date,
            joke=excluded.joke,
            greeting=excluded.greeting
    """, (
        city,
        content_date,
        joke,
        greeting
    ))

    conn.commit()
    conn.close()