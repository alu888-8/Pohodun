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