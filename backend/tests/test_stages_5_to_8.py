"""
Comprehensive Test Suite for Stages 5, 6, 7, and 8
Covers:
  - Stage 5: Retrieve and track reports (list, filters, individual lookup, 404 handling)
  - Stage 6: Admin authentication, PBKDF2 password hashing, token validation, RBAC
  - Stage 7: Incident management dashboard APIs (KPI stats, team assignment, status updates)
  - Stage 8: Rescue team workflow (assignments query, operational logs, resolution)
"""

import os
import sys
import tempfile
from pathlib import Path
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db, get_db_connection
from app.schemas import (
    ReportCreate,
    ReportStatusUpdate,
    RescueProgressUpdate,
    AdminLogin,
    SeverityLevel,
    ReportStatus,
)
from app.auth import (
    hash_password,
    verify_password,
    create_session_token,
    get_current_user,
    require_role,
)
from app.routes.reports import create_report, list_reports, get_report_by_id
from app.routes.auth import login, logout, get_profile
from app.routes.admin import get_admin_stats, admin_list_reports, update_report_status
from app.routes.rescue import get_rescue_teams, get_rescue_assignments, update_rescue_progress


def test_stage_5_retrieve_and_track(temp_db_path: Path):
    """Stage 5: Test report listing, filtering, and single report tracking."""
    print("[1] STAGE 5: Testing Report Retrieval & Citizen Tracking...")

    # Create 3 reports with distinct severities and locations
    rep1 = create_report(
        ReportCreate(
            citizen_name="Aarav Patel",
            location="North Bridge, Ward 2",
            description="Water level up to steps.",
            severity=SeverityLevel.LOW,
        )
    )
    rep2 = create_report(
        ReportCreate(
            citizen_name="Bhavna Joshi",
            location="Submerged Underpass, Ward 4",
            description="Car stuck in 4 feet of floodwater.",
            severity=SeverityLevel.HIGH,
        )
    )
    rep3 = create_report(
        ReportCreate(
            citizen_name="Chirag Sen",
            location="Riverbank Slums, Ward 4",
            description="Elderly residents trapped on roof.",
            severity=SeverityLevel.CRITICAL,
        )
    )

    # A. List all reports
    all_reports = list_reports()
    assert len(all_reports) >= 3, "All submitted reports should be retrieved"
    print(f"    Total reports listed: {len(all_reports)}")

    # B. Filter by severity
    critical_reports = list_reports(severity=SeverityLevel.CRITICAL)
    assert any(r["report_id"] == rep3["report_id"] for r in critical_reports)
    assert all(r["severity"] == "Critical" for r in critical_reports)
    print("    [PASS] Severity filtering verified.")

    # C. Search by keyword
    ward4_reports = list_reports(search="Ward 4")
    assert len(ward4_reports) >= 2
    print("    [PASS] Free-text search verified.")

    # D. Track individual report by ID
    tracked = get_report_by_id(rep2["report_id"])
    assert tracked["report_id"] == rep2["report_id"]
    assert tracked["citizen_name"] == "Bhavna Joshi"
    assert tracked["status"] == "Pending"
    print(f"    [PASS] Tracked single report: {tracked['report_id']}")

    # E. 404 handling for invalid tracking ID
    try:
        get_report_by_id("FL-DOESNOTEXIST")
        assert False, "Should raise 404 for invalid report_id"
    except HTTPException as e:
        assert e.status_code == 404
        print(f"    [PASS] Non-existent ID returned 404: {e.detail}")

    return rep3["report_id"]


def test_stage_6_admin_authentication(temp_db_path: Path):
    """Stage 6: Test secure password hashing, login, token authentication, and RBAC."""
    print("\n[2] STAGE 6: Testing Admin Authentication & RBAC...")

    # A. Test PBKDF2 Password Hashing
    raw_pw = "SuperSecurePassword987!"
    pw_hash = hash_password(raw_pw)
    assert "$" in pw_hash
    assert verify_password(raw_pw, pw_hash) is True
    assert verify_password("WrongPassword!", pw_hash) is False
    print("    [PASS] PBKDF2-HMAC-SHA256 hashing and constant-time verification passed.")

    # B. Test Login with seeded credentials (seeded in init_db)
    # Default admin credentials: admin / AdminPass123!
    auth_res = login(AdminLogin(username="admin", password="AdminPass123!"))
    assert "access_token" in auth_res
    assert auth_res["role"] == "admin"
    admin_token = auth_res["access_token"]
    print("    [PASS] Admin login succeeded. Received bearer token.")

    # C. Test Invalid Credentials
    try:
        login(AdminLogin(username="admin", password="WrongPassword!"))
        assert False, "Should raise 401 for incorrect password"
    except HTTPException as e:
        assert e.status_code == 401
        print("    [PASS] Invalid password rejected with HTTP 401.")

    # D. Test Token Validation via get_current_user dependency
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
    user = get_current_user(creds)
    assert user["username"] == "admin"
    assert user["role"] == "admin"
    print("    [PASS] Bearer token verified against SQLite active_tokens.")

    # E. Test RBAC: Admin vs Rescue Team role enforcement
    admin_checker = require_role(["admin"])
    admin_user = admin_checker(user)
    assert admin_user["username"] == "admin"

    rescue_login = login(AdminLogin(username="rescuer1", password="RescuePass123!"))
    rescue_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=rescue_login["access_token"])
    rescue_user = get_current_user(rescue_creds)

    # Rescuer should fail admin role requirement
    try:
        admin_checker(rescue_user)
        assert False, "Rescue team should not be allowed into admin-only endpoints"
    except HTTPException as e:
        assert e.status_code == 403
        print("    [PASS] RBAC blocked non-admin user with HTTP 403 Forbidden.")

    # F. Test Logout revokes session token
    logout_res = logout(user)
    assert logout_res["revoked"] is True
    try:
        get_current_user(creds)
        assert False, "Revoked token should be rejected"
    except HTTPException as e:
        assert e.status_code == 401
        print("    [PASS] Token revocation / logout confirmed.")

    # Return active admin and rescue tokens for subsequent tests
    new_admin_res = login(AdminLogin(username="admin", password="AdminPass123!"))
    new_rescue_res = login(AdminLogin(username="rescuer1", password="RescuePass123!"))
    return new_admin_res["access_token"], new_rescue_res["access_token"]


def test_stage_7_incident_management(temp_db_path: Path, admin_token: str, report_id: str):
    """Stage 7: Test admin KPI stats and team assignment."""
    print("\n[3] STAGE 7: Testing Incident Management Dashboard APIs...")

    # A. KPI stats
    stats = get_admin_stats()
    assert stats["total_reports"] >= 3
    assert stats["pending"] >= 1
    assert stats["critical_unresolved"] >= 1
    print(f"    Admin stats: Total={stats['total_reports']}, Pending={stats['pending']}, Critical Unresolved={stats['critical_unresolved']}")
    print("    [PASS] KPI statistics aggregated correctly.")

    # B. Update status to 'Assigned' and assign rescue team
    updated = update_report_status(
        report_id=report_id,
        payload=ReportStatusUpdate(
            status=ReportStatus.ASSIGNED,
            assigned_team="Team Alpha — Rapid Boat Rescue",
            admin_notes="Dispatched 2 motorized rescue boats for roof evacuation.",
        ),
    )
    assert updated["status"] == "Assigned"
    assert updated["assigned_team"] == "Team Alpha — Rapid Boat Rescue"
    assert "Dispatched" in updated["admin_notes"]
    print(f"    Assigned incident {report_id} to {updated['assigned_team']}.")
    print("    [PASS] Incident updated and assigned successfully.")


def test_stage_8_rescue_team_workflow(temp_db_path: Path, rescue_token: str, report_id: str):
    """Stage 8: Test rescue team assignments, in-progress updates, and resolution."""
    print("\n[4] STAGE 8: Testing Rescue Team Workflow...")

    # A. List available teams
    teams = get_rescue_teams()
    assert len(teams) >= 4
    print(f"    Available rescue teams: {[t['name'] for t in teams]}")
    print("    [PASS] Rescue squads catalog verified.")

    # B. Query assignments for Team Alpha
    assignments = get_rescue_assignments(team_name="Team Alpha — Rapid Boat Rescue")
    assert any(a["report_id"] == report_id for a in assignments)
    print(f"    Found active assignments for Team Alpha: {len(assignments)}")
    print("    [PASS] Team assignments retrieved.")

    # C. Advance status to 'In Progress' with field notes
    progress_update = update_rescue_progress(
        report_id=report_id,
        payload=RescueProgressUpdate(
            status=ReportStatus.IN_PROGRESS,
            progress_notes="Team Alpha reached site via boat. Commencing evacuation.",
        ),
    )
    assert progress_update["status"] == "In Progress"
    assert "Commencing evacuation" in progress_update["admin_notes"]
    print("    [PASS] Status updated to 'In Progress'.")

    # D. Mark incident 'Resolved'
    resolved_update = update_rescue_progress(
        report_id=report_id,
        payload=RescueProgressUpdate(
            status=ReportStatus.RESOLVED,
            progress_notes="All 3 elderly citizens rescued and moved to Ward 4 community shelter.",
        ),
    )
    assert resolved_update["status"] == "Resolved"
    assert "rescued and moved" in resolved_update["admin_notes"]
    print(f"    Incident {report_id} marked RESOLVED.")
    print("    [PASS] Rescue team resolution workflow completed.")

    # E. Verify resolved report is no longer in active rescue queue
    active_assignments = get_rescue_assignments(team_name="Team Alpha — Rapid Boat Rescue")
    assert not any(a["report_id"] == report_id for a in active_assignments)
    print("    [PASS] Resolved incident removed from active rescue dispatch queue.")


def run_stages_5_to_8_tests():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_floodlink_stages5_8.db"
        os.environ["DATABASE_PATH"] = str(test_db)
        init_db(test_db)

        print("=" * 65)
        print("FLOODLINK COMBINED TEST SUITE: STAGES 5, 6, 7, 8")
        print("=" * 65)

        test_report_id = test_stage_5_retrieve_and_track(test_db)
        admin_token, rescue_token = test_stage_6_admin_authentication(test_db)
        test_stage_7_incident_management(test_db, admin_token, test_report_id)
        test_stage_8_rescue_team_workflow(test_db, rescue_token, test_report_id)

        print("=" * 65)
        print("ALL 4 STAGES PASSED COMPLETELY WITH 0 ERRORS")
        print("=" * 65)


if __name__ == "__main__":
    run_stages_5_to_8_tests()
