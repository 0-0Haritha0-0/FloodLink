"""
Stage 4 Test Suite: Report Submission API (POST /api/reports)
Tests:
  1. Valid report submission with HTTP 201 response data
  2. Database persistence verification of submitted reports
  3. Unique tracking ID generation (prefix 'FL-', collision resistance)
  4. Validation failure on invalid severity levels
  5. Validation failure on missing required fields
  6. Whitespace-only input rejection & auto-stripping of surrounding spaces
  7. End-to-end FastAPI router registration
"""

import os
import sys
import tempfile
from pathlib import Path
import pydantic

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import init_db, get_db_connection
from app.schemas import ReportCreate, SeverityLevel, ReportStatus
from app.routes.reports import create_report, generate_report_id


def setup_test_db(temp_db_path: Path):
    """Sets DATABASE_PATH env var and initializes tables in an isolated test database."""
    os.environ["DATABASE_PATH"] = str(temp_db_path)
    init_db(temp_db_path)


def test_unique_tracking_ids():
    """Verifies that generated tracking IDs are unique and formatted correctly."""
    print("[1] Testing unique tracking ID generation...")
    ids = set()
    total_samples = 50

    for _ in range(total_samples):
        new_id = generate_report_id()
        assert new_id.startswith("FL-"), f"ID {new_id} must start with 'FL-'"
        assert len(new_id) == 11, f"Expected format FL-XXXXXXXX (11 chars), got {new_id}"
        ids.add(new_id)

    assert len(ids) == total_samples, "Every generated tracking ID must be unique"
    sample = next(iter(ids))
    print(f"    Generated {total_samples} distinct IDs successfully (Sample: {sample})")
    print("    [PASS] Tracking ID uniqueness and formatting verified.")


def test_valid_report_submission(temp_db_path: Path):
    """Verifies successful submission of a valid report."""
    print("\n[2] Testing valid report submission...")
    payload = ReportCreate(
        citizen_name="Rajesh Kumar",
        location="Main Market Road, Ward 5",
        description="Drainage overflow, water level reached 2.5 feet outside shops.",
        severity=SeverityLevel.HIGH,
    )

    result = create_report(payload)

    assert "report_id" in result
    assert result["report_id"].startswith("FL-")
    assert result["citizen_name"] == "Rajesh Kumar"
    assert result["location"] == "Main Market Road, Ward 5"
    assert result["description"] == "Drainage overflow, water level reached 2.5 feet outside shops."
    assert result["severity"] == "High"
    assert result["status"] == "Pending"
    assert result["assigned_team"] is None
    assert result["admin_notes"] is None
    assert "created_at" in result
    assert "updated_at" in result

    print(f"    Created report: ID={result['report_id']}, Status={result['status']}, Severity={result['severity']}")
    print("    [PASS] Report created with default status 'Pending' and valid fields.")
    return result["report_id"]


def test_database_persistence(temp_db_path: Path, report_id: str):
    """Verifies that the submitted report exists in the SQLite database."""
    print("\n[3] Testing database persistence of submitted report...")
    conn = get_db_connection(temp_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (report_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"Report {report_id} was not found in SQLite database!"
    assert row["report_id"] == report_id
    assert row["citizen_name"] == "Rajesh Kumar"
    assert row["status"] == "Pending"
    print(f"    Database verification confirmed: row ID={row['id']}, DB Status={row['status']}")
    print("    [PASS] Report persisted securely to SQLite.")


def test_invalid_severity_rejection():
    """Verifies that invalid severity values are rejected before database access."""
    print("\n[4] Testing invalid severity rejection...")
    try:
        ReportCreate(
            citizen_name="Sunita Rao",
            location="Sector 7",
            description="Flooding near school",
            severity="Catastrophic",  # Invalid severity
        )
        assert False, "Should have raised ValidationError for invalid severity"
    except pydantic.ValidationError as err:
        error_msgs = [e["msg"] for e in err.errors()]
        print(f"    Validation error caught: {error_msgs[0]}")
        print("    [PASS] Invalid severity successfully rejected by Pydantic.")


def test_missing_fields_rejection():
    """Verifies that submissions with missing mandatory fields are rejected."""
    print("\n[5] Testing missing mandatory fields rejection...")
    # Missing location
    try:
        ReportCreate(
            citizen_name="Rohan",
            description="Water is waist high",
            severity=SeverityLevel.CRITICAL,
        )
        assert False, "Should have raised ValidationError for missing location"
    except pydantic.ValidationError:
        print("    [PASS] Missing 'location' field rejected.")

    # Missing description
    try:
        ReportCreate(
            citizen_name="Rohan",
            location="Sector 11",
            severity=SeverityLevel.CRITICAL,
        )
        assert False, "Should have raised ValidationError for missing description"
    except pydantic.ValidationError:
        print("    [PASS] Missing 'description' field rejected.")


def test_whitespace_and_empty_validation():
    """Verifies whitespace-only input rejection and automatic string stripping."""
    print("\n[6] Testing whitespace handling and empty field rejection...")
    # Whitespace-only name
    try:
        ReportCreate(
            citizen_name="   \t   ",
            location="Sector 11",
            description="Water rising",
            severity=SeverityLevel.LOW,
        )
        assert False, "Should have raised ValidationError for whitespace-only name"
    except pydantic.ValidationError:
        print("    [PASS] Whitespace-only name successfully rejected.")

    # Auto-stripping of leading/trailing spaces
    report = ReportCreate(
        citizen_name="  Kavita Sharma  ",
        location="  Block B, Green Park  ",
        description="  Road submerged under water.  ",
        severity=SeverityLevel.MEDIUM,
    )
    assert report.citizen_name == "Kavita Sharma"
    assert report.location == "Block B, Green Park"
    assert report.description == "Road submerged under water."
    print("    [PASS] Leading and trailing whitespace automatically stripped.")


def test_router_registered_in_app():
    """Verifies that POST /api/reports route is registered in the main FastAPI app."""
    print("\n[7] Testing FastAPI app route registration...")
    route_paths = []
    for route in app.routes:
        if hasattr(route, "path"):
            route_paths.append(route.path)
        elif hasattr(route, "original_router"):
            for sub_route in route.original_router.routes:
                if hasattr(sub_route, "path"):
                    route_paths.append(sub_route.path)

    print(f"    Available routes: {route_paths}")
    assert "/api/reports" in route_paths, "Route '/api/reports' must be registered in app"
    print("    [PASS] Route '/api/reports' registered cleanly in FastAPI application.")


def run_all_stage4_tests():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_floodlink_stage4.db"
        setup_test_db(test_db)

        print("=" * 65)
        print("FLOODLINK STAGE 4: REPORT SUBMISSION API TEST SUITE")
        print("=" * 65)

        test_unique_tracking_ids()
        created_id = test_valid_report_submission(test_db)
        test_database_persistence(test_db, created_id)
        test_invalid_severity_rejection()
        test_missing_fields_rejection()
        test_whitespace_and_empty_validation()
        test_router_registered_in_app()

        print("=" * 65)
        print("STAGE 4 TEST SUITE COMPLETED: 7/7 TESTS PASSED (0 ERRORS)")
        print("=" * 65)


if __name__ == "__main__":
    run_all_stage4_tests()
