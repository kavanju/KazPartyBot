import sqlite3
import time

db = sqlite3.connect("data.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    created INTEGER,
    paid_until INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    user_id INTEGER,
    query TEXT,
    time INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS saved_places (
    user_id INTEGER,
    place TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    place TEXT,
    user_id INTEGER,
    rating INTEGER,
    comment TEXT,
    time INTEGER
)
""")

db.commit()

def save_user(user_id, paid=False):
    now = int(time.time())
    paid_until = now + 48*3600 if paid else 0
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, now, paid_until))
    db.commit()

def check_access(user_id):
    row = cursor.execute("SELECT paid_until FROM users WHERE user_id=?", (user_id,)).fetchone()
    if row:
        return row[0] > int(time.time())
    return False

def log_request(user_id, query):
    cursor.execute("INSERT INTO requests VALUES (?, ?, ?)", (user_id, query, int(time.time())))
    db.commit()

def save_place(user_id, place):
    cursor.execute("INSERT INTO saved_places VALUES (?, ?)", (user_id, place))
    db.commit()

def get_saved_places(user_id):
    rows = cursor.execute("SELECT place FROM saved_places WHERE user_id=?", (user_id,)).fetchall()
    return [r[0] for r in rows]

def save_review(user_id, place, rating, comment):
    cursor.execute("INSERT INTO reviews VALUES (?, ?, ?, ?, ?)", (place, user_id, rating, comment, int(time.time())))
    db.commit()