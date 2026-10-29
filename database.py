"""Gestione del database SQLite dell'applicazione."""

import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'admin')) DEFAULT 'user',
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_ref TEXT NOT NULL,
    game TEXT NOT NULL CHECK (game IN ('phrase', 'clue', 'synonym', 'complete')),
    level TEXT NOT NULL CHECK (level IN ('facile', 'medio', 'difficile')),
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= total),
    total INTEGER NOT NULL CHECK (total = 3),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds >= 0),
    played_at TEXT NOT NULL,
    UNIQUE (user_id, client_ref)
);

CREATE INDEX IF NOT EXISTS idx_game_sessions_user_date
    ON game_sessions (user_id, played_at DESC);

CREATE TABLE IF NOT EXISTS login_attempts (
    ip_address TEXT PRIMARY KEY,
    failures INTEGER NOT NULL,
    window_started_at INTEGER NOT NULL
);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        g.db = connection
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    connection = get_db()
    connection.executescript(SCHEMA)
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "username" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN username TEXT COLLATE NOCASE")
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique "
        "ON users(username COLLATE NOCASE) WHERE username IS NOT NULL"
    )
    connection.commit()
