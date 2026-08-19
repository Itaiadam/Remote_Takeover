import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "commands.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            worker_ip TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    return conn

def insert_message(sender, recipient, worker_ip, message, timestamp):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO messages (sender, recipient, worker_ip, message, timestamp) VALUES (?, ?, ?, ?, ?)",
            (sender, recipient, worker_ip, message, timestamp)
        )
    conn.close()