import sqlite3

DB_PATH = "db/tasks.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT CHECK(status IN ('pending', 'done')) DEFAULT 'pending',
            due_at DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
            );
        """)

        conn.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


def get_or_create_user(telegram_user_id, username=None, first_name=None):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,)
        ).fetchone()

        if user:
            return user["id"]

        conn.execute(
            """
            INSERT INTO users (telegram_user_id, username, first_name)
            VALUES (?, ?, ?)
            """,
            (telegram_user_id, username, first_name)
        )

        return conn.execute(
            "SELECT id FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,)
        ).fetchone()["id"]


def task_exists(user_id, *, task_id=None, title=None):
    if task_id is not None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM tasks
                WHERE user_id = ?
                  AND id = ?
                  AND status = 'pending'
                """,
                (user_id, task_id)
            ).fetchone()
        return row is not None

    elif title is not None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM tasks
                WHERE user_id = ?
                  AND lower(title) = lower(?)
                  AND status = 'pending'
                """,
                (user_id, title.strip())
            ).fetchone()
        return row is not None

    else:
        raise ValueError("task_id or title required")


def add_task(user_id, title, description=None, due_at=None, category_id=None):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks (user_id, title, description, due_at, category_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, title, description, due_at, category_id)
        )



def get_pending_tasks(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, category_id, due_at
            FROM tasks
            WHERE user_id = ? AND status = 'pending'
            ORDER BY due_at ASC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def mark_task_done(user_id, task_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'done',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id)
        )

def category_exists(user_id, name):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM categories
            WHERE user_id = ? AND lower(name) = lower(?)
            """,
            (user_id, name)
        ).fetchone()
        return row is not None

def create_category(user_id, name, description=None):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO categories (user_id, name, description)
            VALUES (?, ?, ?)
            """,
            (user_id, name, description)
        )

def get_categories(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name
            FROM categories
            WHERE user_id = ?
            ORDER BY name
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]



