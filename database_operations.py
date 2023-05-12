import sqlite3
from pathlib import Path

THIS_FOLDER = Path(__file__).parent.resolve()


def connection():
    return sqlite3.connect(f'{THIS_FOLDER}/bot_database.db', check_same_thread=False)


def create_users_table():
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            username TEXT,
            is_admin INTEGER,
            is_active INTEGER
        );''')


def get_user_ids():
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        user_ids = [row[0] for row in cursor.fetchall()]
        return user_ids


def add_user(user_id, first_name, last_name, username):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?, 0, 0)',
                       (user_id, first_name, last_name, '', username))
        conn.commit()


def set_user_email(user_id, email):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET email=? WHERE user_id=?', (email, user_id))
        conn.commit()


def is_user_active(user_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_active FROM users WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        return row is not None and row[0] == 1


def set_user_active(user_id, is_active):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active=? WHERE user_id=?', (is_active, user_id))
        conn.commit()


def get_user_email(user_id):
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM users WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        return row[0] if row is not None else None


def get_users():
    with connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        rows = cursor.fetchall()
        return rows
