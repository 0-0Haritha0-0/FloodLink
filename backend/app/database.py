"""
FloodLink Database Management Module
Uses Python's built-in sqlite3 module to manage SQLite database connections,
schema definitions, and automatic table initialization.

Cybersecurity & Reliability Principles:
- Parameterized queries ONLY (prevents SQL Injection).
- Explicit column constraints (CHECK, NOT NULL, UNIQUE) for defense-in-depth data integrity.
- sqlite3.Row row factory for type-safe dictionary-style column access.
- WAL (Write-Ahead Logging) mode and foreign keys enabled by default.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional


# Default path for the SQLite database file: floodlink/backend/floodlink.db
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "floodlink.db"


def get_db_path() -> Path:
    """
    Returns the resolved database path, respecting the DATABASE_PATH
    environment variable if configured (useful for automated testing).
    """
    custom_path = os.getenv("DATABASE_PATH")
    if custom_path:
        return Path(custom_path)
    return DEFAULT_DB_PATH


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Creates and returns a new SQLite connection with best-practice configurations:
    - row_factory = sqlite3.Row: Enables accessing columns by name (e.g., row['report_id']).
    - foreign_keys = ON: Enforces referential integrity.
    - WAL mode: Enhances concurrent read/write throughput without file-locking contention.
    """
    target_path = db_path or get_db_path()
    
    # Ensure the parent directory exists if using a file path
    if str(target_path) != ":memory:":
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Enable Write-Ahead Logging if persistent file
    if str(target_path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")

    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """
    Initializes the SQLite database and creates all required tables and indexes
    if they do not already exist. Safe to run multiple times (idempotent).
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    try:
        # Table 1: reports - Stores citizen emergency SOS requests
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE NOT NULL,
                citizen_name TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
                status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Assigned', 'In Progress', 'Resolved')),
                assigned_team TEXT DEFAULT NULL,
                admin_notes TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # Indexes for reports: Speed up lookups by report_id, status, and severity
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_report_id ON reports(report_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_severity ON reports(severity);"
        )

        # Table 2: admins - Stores authorized staff / administrative credentials
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin' CHECK(role IN ('admin', 'rescue_team')),
                created_at TEXT NOT NULL
            );
            """
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);"
        )

        # Table 3: active_tokens - Persists authenticated session tokens
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS active_tokens (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tokens_username ON active_tokens(username);"
        )

        # Seed default administrative and rescue accounts if empty
        cursor.execute("SELECT COUNT(*) as count FROM admins;")
        if cursor.fetchone()["count"] == 0:
            from datetime import datetime, timezone
            from app.auth import hash_password

            now_iso = datetime.now(timezone.utc).isoformat()
            default_admin_pw = os.getenv("ADMIN_DEFAULT_PASSWORD", "AdminPass123!")
            default_rescue_pw = os.getenv("RESCUE_DEFAULT_PASSWORD", "RescuePass123!")

            cursor.execute(
                """
                INSERT INTO admins (username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?);
                """,
                ("admin", hash_password(default_admin_pw), "admin", now_iso),
            )
            cursor.execute(
                """
                INSERT INTO admins (username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?);
                """,
                ("rescuer1", hash_password(default_rescue_pw), "rescue_team", now_iso),
            )

        conn.commit()
    finally:
        conn.close()
