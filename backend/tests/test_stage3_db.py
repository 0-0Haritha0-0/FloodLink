"""
Stage 3 Test Suite: SQLite Database & Automatic Table Initialization
Tests:
  1. Automatic table and index creation (idempotent init_db)
  2. Table schema & column structure verification
  3. Database-level constraints & data integrity (CHECK, UNIQUE constraints)
  4. SQL Injection safety via parameterized queries
  5. Data persistence across database connection closings and reopenings
  6. sqlite3.Row dictionary-style column access
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_db_connection, init_db


def test_init_db_creates_tables(temp_db_path: Path):
    """Verifies that init_db creates the database and expected tables idempotently."""
    print("[1] Testing database and table initialization...")

    # Run initialization twice to verify idempotence (CREATE TABLE IF NOT EXISTS)
    init_db(temp_db_path)
    init_db(temp_db_path)

    conn = get_db_connection(temp_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    conn.close()

    print(f"    Discovered tables: {tables}")
    assert "reports" in tables, "Table 'reports' must exist"
    assert "admins" in tables, "Table 'admins' must exist"
    print("    [PASS] Tables initialized successfully without error.")


def test_table_columns_and_indexes(temp_db_path: Path):
    """Verifies the column names and indexes for the reports table."""
    print("\n[2] Verifying table columns and indexes...")
    conn = get_db_connection(temp_db_path)
    cursor = conn.cursor()

    # Inspect 'reports' columns
    cursor.execute("PRAGMA table_info(reports);")
    columns = {row["name"]: row["type"] for row in cursor.fetchall()}
    print(f"    'reports' columns: {list(columns.keys())}")

    expected_columns = [
        "id",
        "report_id",
        "citizen_name",
        "location",
        "description",
        "severity",
        "status",
        "assigned_team",
        "admin_notes",
        "created_at",
        "updated_at",
    ]
    for col in expected_columns:
        assert col in columns, f"Column '{col}' missing from reports table"

    # Inspect indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row["name"] for row in cursor.fetchall()]
    print(f"    Discovered indexes: {indexes}")
    assert "idx_reports_report_id" in indexes
    assert "idx_reports_status" in indexes
    assert "idx_reports_severity" in indexes
    assert "idx_admins_username" in indexes

    conn.close()
    print("    [PASS] All expected columns and indexes verified.")


def test_database_constraints(temp_db_path: Path):
    """Verifies SQL CHECK and UNIQUE constraints enforce data integrity."""
    print("\n[3] Testing database-level constraints (CHECK & UNIQUE)...")
    conn = get_db_connection(temp_db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    # A. Test CHECK constraint on invalid severity
    try:
        conn.execute(
            """
            INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("FL-TEST-1", "Test Citizen", "Sector 3", "Water rising", "INVALID_SEVERITY", "Pending", now_iso, now_iso),
        )
        conn.commit()
        assert False, "Should have raised IntegrityError for invalid severity"
    except sqlite3.IntegrityError:
        print("    [PASS] CHECK constraint prevented invalid severity value.")

    # B. Test CHECK constraint on invalid status
    try:
        conn.execute(
            """
            INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("FL-TEST-2", "Test Citizen", "Sector 3", "Water rising", "High", "INVALID_STATUS", now_iso, now_iso),
        )
        conn.commit()
        assert False, "Should have raised IntegrityError for invalid status"
    except sqlite3.IntegrityError:
        print("    [PASS] CHECK constraint prevented invalid status value.")

    # C. Test UNIQUE constraint on report_id
    conn.execute(
        """
        INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("FL-UNIQUE-1", "Citizen 1", "Sector 3", "Water rising", "Medium", "Pending", now_iso, now_iso),
    )
    conn.commit()

    try:
        conn.execute(
            """
            INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("FL-UNIQUE-1", "Citizen 2", "Sector 5", "Tree blocked road", "Low", "Pending", now_iso, now_iso),
        )
        conn.commit()
        assert False, "Should have raised IntegrityError for duplicate report_id"
    except sqlite3.IntegrityError:
        print("    [PASS] UNIQUE constraint prevented duplicate report_id.")

    conn.close()


def test_sql_injection_defense_and_parameterized_queries(temp_db_path: Path):
    """
    Verifies that parameterized queries safely neutralize SQL Injection attacks.
    Tests injection vectors like quote escapes and query terminators.
    """
    print("\n[4] Testing SQL Injection defense via parameterized queries...")
    conn = get_db_connection(temp_db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Classic SQL Injection attack payload
    sqli_payload = "Robert'); DROP TABLE reports; --"
    report_id = "FL-SQLI-TEST"

    # Parameterized insert
    conn.execute(
        """
        INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (report_id, sqli_payload, "Safe Zone", "Testing SQLi neutralization", "High", "Pending", now_iso, now_iso),
    )
    conn.commit()

    # Verify the table was NOT dropped and the payload was stored harmlessly as literal data
    cursor = conn.cursor()
    cursor.execute("SELECT citizen_name, location FROM reports WHERE report_id = ?;", (report_id,))
    row = cursor.fetchone()

    assert row is not None, "Record must exist"
    assert row["citizen_name"] == sqli_payload, "Payload must be treated strictly as data string"
    print(f"    Neutralized payload stored safely as string: '{row['citizen_name']}'")

    # Verify reports table is still fully operational
    cursor.execute("SELECT COUNT(*) as count FROM reports;")
    count = cursor.fetchone()["count"]
    assert count >= 1
    conn.close()
    print("    [PASS] SQL Injection payload completely neutralized by parameterized query.")


def test_database_persistence_across_connections(temp_db_path: Path):
    """
    Verifies that records written to the SQLite database file persist across
    closing connections, reopening connections, and checking row data.
    """
    print("\n[5] Testing database persistence across reconnections...")
    report_id = "FL-PERSIST-99"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Connection 1: Insert record and close
    conn1 = get_db_connection(temp_db_path)
    conn1.execute(
        """
        INSERT INTO reports (report_id, citizen_name, location, description, severity, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (report_id, "Devon Clark", "Riverbank St", "Rising river water", "Critical", "Pending", now_iso, now_iso),
    )
    conn1.commit()
    conn1.close()

    # Connection 2: Reopen from file and assert data persisted
    conn2 = get_db_connection(temp_db_path)
    cursor = conn2.cursor()
    cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (report_id,))
    row = cursor.fetchone()

    assert row is not None, "Data must persist across connection closes"
    assert row["citizen_name"] == "Devon Clark"
    assert row["severity"] == "Critical"
    assert row["status"] == "Pending"

    # Test dictionary conversion via sqlite3.Row
    row_dict = dict(row)
    assert row_dict["report_id"] == report_id
    assert "id" in row_dict
    print("    Retrieved persistent row:", row_dict)

    # Connection 2: Update status to 'Assigned' and assign a team
    conn2.execute(
        """
        UPDATE reports
        SET status = ?, assigned_team = ?, updated_at = ?
        WHERE report_id = ?;
        """,
        ("Assigned", "Rescue Team Alpha", datetime.now(timezone.utc).isoformat(), report_id),
    )
    conn2.commit()
    conn2.close()

    # Connection 3: Verify the update persisted
    conn3 = get_db_connection(temp_db_path)
    updated_row = conn3.execute("SELECT status, assigned_team FROM reports WHERE report_id = ?;", (report_id,)).fetchone()
    assert updated_row["status"] == "Assigned"
    assert updated_row["assigned_team"] == "Rescue Team Alpha"
    conn3.close()

    print("    [PASS] Data persisted and updated across separate connections successfully.")


def run_all_stage3_tests():
    # Use a clean temporary SQLite database file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_floodlink.db"
        print("=" * 65)
        print("FLOODLINK STAGE 3 DATABASE TEST SUITE")
        print(f"Testing isolated database at: {test_db}")
        print("=" * 65)

        test_init_db_creates_tables(test_db)
        test_table_columns_and_indexes(test_db)
        test_database_constraints(test_db)
        test_sql_injection_defense_and_parameterized_queries(test_db)
        test_database_persistence_across_connections(test_db)

        print("=" * 65)
        print("STAGE 3 TEST SUITE COMPLETED: 5/5 TEST CATEGORIES PASSED (0 ERRORS)")
        print("=" * 65)


if __name__ == "__main__":
    run_all_stage3_tests()
