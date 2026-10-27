"""
End-to-End System Integration Test
Simulates the entire real-world lifecycle from citizen SOS submission through
coordinator triage, team assignment, rescue field operation, and final resolution.
"""

import os
import sys
import tempfile
from pathlib import Path

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
from app.routes.reports import create_report, get_report_by_id, list_reports
from app.routes.auth import login
from app.routes.admin import get_admin_stats, update_report_status
from app.routes.rescue import get_rescue_assignments, update_rescue_progress


def run_e2e_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "e2e_floodlink.db"
        os.environ["DATABASE_PATH"] = str(test_db)
        init_db(test_db)

        print("=" * 70)
        print("FLOODLINK END-TO-END SYSTEM INTEGRATION TEST")
        print(f"Isolated SQLite database: {test_db}")
        print("=" * 70)

        # -------------------------------------------------------------
        # STEP 1: Citizen SOS Submission
        # -------------------------------------------------------------
        print("\n[Step 1] Citizen submits SOS report (POST /api/reports)...")
        citizen_payload = ReportCreate(
            citizen_name="Siddharth Roy",
            location="Near Metro Station, Sector 4, Ward 7",
            description="Water level 4 feet. 5 people stranded on rooftop.",
            severity=SeverityLevel.CRITICAL,
        )
        report_res = create_report(citizen_payload)
        tracking_id = report_res["report_id"]
        print(f"    Report created successfully: ID={tracking_id}")
        assert tracking_id.startswith("FL-")
        assert report_res["status"] == "Pending"
        assert report_res["severity"] == "Critical"
        print("    [PASS] Step 1: Real tracking ID generated and report stored as Pending.")

        # -------------------------------------------------------------
        # STEP 2: Citizen Tracks Status by ID
        # -------------------------------------------------------------
        print(f"\n[Step 2] Citizen checks status (GET /api/reports/{tracking_id})...")
        tracked = get_report_by_id(tracking_id)
        assert tracked["report_id"] == tracking_id
        assert tracked["status"] == "Pending"
        assert tracked["assigned_team"] is None
        print(f"    Citizen UI displays: Status={tracked['status']}, Assigned={tracked['assigned_team']}")
        print("    [PASS] Step 2: Citizen tracking reflects live SQLite data.")

        # -------------------------------------------------------------
        # STEP 3: Public Incident Feed
        # -------------------------------------------------------------
        print("\n[Step 3] Checking Public Incident Feed (GET /api/reports)...")
        feed = list_reports()
        assert any(r["report_id"] == tracking_id for r in feed)
        print(f"    Incident feed contains {len(feed)} reports, including {tracking_id}.")
        print("    [PASS] Step 3: Public incident feed displays active incidents.")

        # -------------------------------------------------------------
        # STEP 4: Admin Authentication
        # -------------------------------------------------------------
        print("\n[Step 4] Coordinator logs in (POST /api/auth/login)...")
        admin_auth = login(AdminLogin(username="admin", password="AdminPass123!"))
        admin_token = admin_auth["access_token"]
        assert admin_auth["role"] == "admin"
        assert len(admin_token) > 20
        print(f"    Admin authenticated. Bearer token issued for role '{admin_auth['role']}'.")
        print("    [PASS] Step 4: Admin login successful.")

        # -------------------------------------------------------------
        # STEP 5: Admin Inspects KPI Stats
        # -------------------------------------------------------------
        print("\n[Step 5] Coordinator reviews KPI statistics (GET /api/admin/stats)...")
        stats = get_admin_stats()
        assert stats["total_reports"] >= 1
        assert stats["pending"] >= 1
        assert stats["critical_unresolved"] >= 1
        print(f"    KPI Stats: Total={stats['total_reports']}, Pending={stats['pending']}, Critical Unresolved={stats['critical_unresolved']}")
        print("    [PASS] Step 5: Live KPI metrics calculated correctly.")

        # -------------------------------------------------------------
        # STEP 6: Admin Triage & Team Assignment
        # -------------------------------------------------------------
        print(f"\n[Step 6] Admin assigns rescue team to incident {tracking_id}...")
        assigned_report = update_report_status(
            report_id=tracking_id,
            payload=ReportStatusUpdate(
                status=ReportStatus.ASSIGNED,
                assigned_team="Team Alpha — Rapid Boat Rescue",
                admin_notes="Dispatched 2 motorized dinghies for rooftop extraction.",
            ),
        )
        assert assigned_report["status"] == "Assigned"
        assert assigned_report["assigned_team"] == "Team Alpha — Rapid Boat Rescue"
        print(f"    Report status advanced to: {assigned_report['status']}, Team: {assigned_report['assigned_team']}")
        print("    [PASS] Step 6: Incident successfully triaged and assigned.")

        # -------------------------------------------------------------
        # STEP 7: Citizen Sees Assignment on Status Page
        # -------------------------------------------------------------
        print(f"\n[Step 7] Citizen refreshes tracker (GET /api/reports/{tracking_id})...")
        citizen_check_2 = get_report_by_id(tracking_id)
        assert citizen_check_2["status"] == "Assigned"
        assert citizen_check_2["assigned_team"] == "Team Alpha — Rapid Boat Rescue"
        print(f"    Citizen tracker now reflects: Status={citizen_check_2['status']}, Unit={citizen_check_2['assigned_team']}")
        print("    [PASS] Step 7: Citizen UI timeline advanced to Step 2 (Assigned).")

        # -------------------------------------------------------------
        # STEP 8: Rescue Team Field Login
        # -------------------------------------------------------------
        print("\n[Step 8] Rescue field unit logs in (POST /api/auth/login)...")
        rescue_auth = login(AdminLogin(username="rescuer1", password="RescuePass123!"))
        rescue_token = rescue_auth["access_token"]
        assert rescue_auth["role"] == "rescue_team"
        print("    [PASS] Step 8: Rescue team authenticated.")

        # -------------------------------------------------------------
        # STEP 9: Rescue Team Views Dispatched Queue
        # -------------------------------------------------------------
        print("\n[Step 9] Rescue unit queries assignments (GET /api/rescue/assignments)...")
        assignments = get_rescue_assignments(team_name="Team Alpha — Rapid Boat Rescue")
        assert any(a["report_id"] == tracking_id for a in assignments)
        print(f"    Dispatched queue for Team Alpha contains {len(assignments)} emergency incident(s).")
        print("    [PASS] Step 9: Incident appears in rescue team dispatch queue.")

        # -------------------------------------------------------------
        # STEP 10: Rescue Team Updates Progress to 'In Progress'
        # -------------------------------------------------------------
        print("\n[Step 10] Rescue team marks 'In Progress' with field notes...")
        in_prog_res = update_rescue_progress(
            report_id=tracking_id,
            payload=RescueProgressUpdate(
                status=ReportStatus.IN_PROGRESS,
                progress_notes="Team Alpha on site. High water flow. Securing anchor line.",
            ),
        )
        assert in_prog_res["status"] == "In Progress"
        assert "Securing anchor line" in in_prog_res["admin_notes"]
        print(f"    Incident updated to: {in_prog_res['status']}")
        print("    [PASS] Step 10: Progress notes appended and status updated to In Progress.")

        # -------------------------------------------------------------
        # STEP 11: Rescue Team Completes Operation and Marks 'Resolved'
        # -------------------------------------------------------------
        print("\n[Step 11] Rescue team completes evacuation and marks 'Resolved'...")
        resolved_res = update_rescue_progress(
            report_id=tracking_id,
            payload=RescueProgressUpdate(
                status=ReportStatus.RESOLVED,
                progress_notes="All 5 citizens successfully evacuated and transported to Sector 4 relief camp.",
            ),
        )
        assert resolved_res["status"] == "Resolved"
        assert "evacuated and transported" in resolved_res["admin_notes"]
        print(f"    Incident marked: {resolved_res['status']}")
        print("    [PASS] Step 11: Incident marked Resolved with full operational history.")

        # -------------------------------------------------------------
        # STEP 12: Final Citizen Tracking Verification
        # -------------------------------------------------------------
        print(f"\n[Step 12] Citizen does final status check (GET /api/reports/{tracking_id})...")
        final_check = get_report_by_id(tracking_id)
        assert final_check["status"] == "Resolved"
        assert "evacuated and transported" in final_check["admin_notes"]
        print(f"    Citizen tracker shows: 100% Complete — Status: {final_check['status']}")
        print("    [PASS] Step 12: End-to-end full lifecycle verified with 100% data integrity!")

        print("\n" + "=" * 70)
        print("END-TO-END INTEGRATION TEST: ALL 12 LIFECYCLE STEPS PASSED (0 ERRORS)")
        print("=" * 70)


if __name__ == "__main__":
    run_e2e_test()
