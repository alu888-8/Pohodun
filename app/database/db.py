import os
import sqlite3


DB_NAME = (
    "/app/database/users.db"
    if os.path.isdir("/app/database")
    else "app/database/users.db"
)


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    # =====================================================
    # КОРИСТУВАЧІ
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,

            city TEXT NOT NULL DEFAULT 'Київ',

            location_key TEXT,

            location_name TEXT,

            location_oblast TEXT
        )
    """)

    # =====================================================
    # МІГРАЦІЯ СТАРОЇ БАЗИ
    # =====================================================

    cursor.execute(
        "PRAGMA table_info(users)"
    )

    columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if "location_key" not in columns:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN location_key TEXT
        """)

    if "location_name" not in columns:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN location_name TEXT
        """)

    if "location_oblast" not in columns:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN location_oblast TEXT
        """)

    # =====================================================
    # КОНТЕНТ ДНЯ
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_content_city (
            city TEXT PRIMARY KEY,
            content_date TEXT NOT NULL,
            joke TEXT NOT NULL,
            greeting TEXT NOT NULL,
            advice TEXT NOT NULL DEFAULT ''
        )
    """)

    # =====================================================
    # СТАН ПЛАНУВАЛЬНИКА
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_state (
            name TEXT PRIMARY KEY,
            last_run_date TEXT
        )
    """)

    conn.commit()
    conn.close()


# =====================================================
# МІСТО
# =====================================================

def get_city(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT city
        FROM users
        WHERE telegram_id=?
    """, (user_id,))

    row = cursor.fetchone()

    if row is None:

        cursor.execute("""
            INSERT INTO users (
                telegram_id,
                city
            )
            VALUES (?, ?)
        """, (
            user_id,
            "Київ"
        ))

        conn.commit()
        conn.close()

        return "Київ"

    conn.close()

    return row[0]


def save_city(
    user_id,
    city
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (
            telegram_id,
            city
        )
        VALUES (?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            city=excluded.city
    """, (
        user_id,
        city
    ))

    conn.commit()
    conn.close()


# =====================================================
# ЛОКАЦІЯ NEPTUN
# =====================================================

def get_location(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            location_key,
            location_name,
            location_oblast
        FROM users
        WHERE telegram_id=?
    """, (
        user_id,
    ))

    row = cursor.fetchone()

    conn.close()

    if not row:

        return None

    if not row[0]:

        return None

    return {
        "key": row[0],
        "name": row[1],
        "oblast": row[2],
    }


def save_location(
    user_id,
    location_key,
    location_name,
    location_oblast
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (
            telegram_id,
            city,
            location_key,
            location_name,
            location_oblast
        )
        VALUES (
            ?,
            COALESCE(
                (
                    SELECT city
                    FROM users
                    WHERE telegram_id=?
                ),
                'Київ'
            ),
            ?,
            ?,
            ?
        )

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            location_key=excluded.location_key,
            location_name=excluded.location_name,
            location_oblast=excluded.location_oblast
    """, (
        user_id,
        user_id,
        location_key,
        location_name,
        location_oblast
    ))

    conn.commit()
    conn.close()


def clear_location(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET
            location_key=NULL,
            location_name=NULL,
            location_oblast=NULL
        WHERE telegram_id=?
    """, (
        user_id,
    ))

    conn.commit()
    conn.close()


# =====================================================
# КОРИСТУВАЧІ
# =====================================================

def get_users_count():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_all_users():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            telegram_id,
            city,
            location_key,
            location_name,
            location_oblast
        FROM users
        ORDER BY telegram_id
    """)

    rows = cursor.fetchall()

    conn.close()

    users = []

    for row in rows:

        users.append({
            "telegram_id": row[0],
            "city": row[1],
            "location_key": row[2],
            "location_name": row[3],
            "location_oblast": row[4],
        })

    return users


# =====================================================
# КОНТЕНТ ДНЯ
# =====================================================

def get_daily_content(city):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            content_date,
            joke,
            greeting,
            advice
        FROM daily_content_city
        WHERE city=?
    """, (
        city,
    ))

    row = cursor.fetchone()

    conn.close()

    if row:

        return {
            "date": row[0],
            "joke": row[1],
            "greeting": row[2],
            "advice": row[3],
        }

    return None


def save_daily_content(
    city,
    content_date,
    joke,
    greeting,
    advice=""
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_content_city (
            city,
            content_date,
            joke,
            greeting,
            advice
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(city)
        DO UPDATE SET
            content_date=excluded.content_date,
            joke=excluded.joke,
            greeting=excluded.greeting,
            advice=excluded.advice
    """, (
        city,
        content_date,
        joke,
        greeting,
        advice,
    ))

    conn.commit()
    conn.close()


# =====================================================
# СТАН ПЛАНУВАЛЬНИКА
# =====================================================

def get_scheduler_last_run(
    name
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT last_run_date
        FROM scheduler_state
        WHERE name=?
    """, (
        name,
    ))

    row = cursor.fetchone()

    conn.close()

    if not row:

        return None

    return row[0]


def set_scheduler_last_run(
    name,
    run_date
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO scheduler_state (
            name,
            last_run_date
        )
        VALUES (?, ?)

        ON CONFLICT(name)
        DO UPDATE SET
            last_run_date=excluded.last_run_date
    """, (
        name,
        run_date,
    ))

    conn.commit()
    conn.close()