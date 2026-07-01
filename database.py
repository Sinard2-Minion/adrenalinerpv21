import sqlite3

DB_NAME = "discord_reviews.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            admin_name TEXT,
            stars INTEGER,
            text TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

def save_review(user_id, username, admin_name, stars, text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (user_id, username, admin_name, stars, text) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, admin_name, stars, text)
    )
    conn.commit()
    conn.close()

def get_next_pending():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, admin_name, stars, text FROM reviews WHERE status = 'pending' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def update_status(review_id, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET status = ? WHERE id = ?", (status, review_id))
    conn.commit()
    conn.close()

def get_review_by_id(review_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, admin_name, stars, text FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    conn.close()
    return row
