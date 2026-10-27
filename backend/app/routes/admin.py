"""
Admin Incident Management Routes
Protected endpoints for emergency managers to verify reports, assign rescue teams,
and monitor disaster metrics.
"""

from datetime import datetime, timezone
from typing import List, Optional
import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db_connection
from app.schemas import (
    ReportResponse,
    ReportStatusUpdate,
    AdminStats,
    SeverityLevel,
    ReportStatus,
)
from app.auth import require_role

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(["admin"]))],  # Enforce admin RBAC across all routes
)


@router.get(
    "/stats",
    response_model=AdminStats,
    summary="Get incident response KPI statistics",
    description="Aggregates live incident statistics for the emergency command center dashboard.",
)
def get_admin_stats():
    """
    Computes key performance indicators (KPIs) from the SQLite database.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM reports;")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as count FROM reports WHERE status = 'Pending';")
        pending = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM reports WHERE status = 'Assigned';")
        assigned = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM reports WHERE status = 'In Progress';")
        in_progress = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM reports WHERE status = 'Resolved';")
        resolved = cursor.fetchone()["count"]

        cursor.execute(
            """
            SELECT COUNT(*) as count FROM reports
            WHERE severity = 'Critical' AND status != 'Resolved';
            """
        )
        critical_unresolved = cursor.fetchone()["count"]

        return {
            "total_reports": total,
            "pending": pending,
            "assigned": assigned,
            "in_progress": in_progress,
            "resolved": resolved,
            "critical_unresolved": critical_unresolved,
        }
    finally:
        conn.close()


@router.get(
    "/reports",
    response_model=List[ReportResponse],
    summary="List all incidents with admin management filters",
)
def admin_list_reports(
    severity: Optional[SeverityLevel] = None,
    status_filter: Optional[ReportStatus] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    Admin view of all reports with flexible sorting and filtering.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM reports WHERE 1=1"
        params = []

        if severity:
            query += " AND severity = ?"
            params.append(severity.value)

        if status_filter:
            query += " AND status = ?"
            params.append(status_filter.value)

        if search and search.strip():
            query += " AND (location LIKE ? OR description LIKE ? OR citizen_name LIKE ? OR report_id LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term, term])

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@router.patch(
    "/reports/{report_id}",
    response_model=ReportResponse,
    summary="Update report status, assign rescue team, or add admin notes",
)
def update_report_status(report_id: str, payload: ReportStatusUpdate):
    """
    Allows emergency coordinator to assign rescue teams and advance request status
    (e.g., Pending -> Assigned -> In Progress -> Resolved).
    """
    cleaned_id = report_id.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check existing report
        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (cleaned_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with tracking ID '{cleaned_id}' not found.",
            )

        # Build dynamic update fields
        cursor.execute(
            """
            UPDATE reports
            SET status = ?, assigned_team = ?, admin_notes = ?, updated_at = ?
            WHERE report_id = ?;
            """,
            (
                payload.status.value,
                payload.assigned_team if payload.assigned_team is not None else existing["assigned_team"],
                payload.admin_notes if payload.admin_notes is not None else existing["admin_notes"],
                now_iso,
                cleaned_id,
            ),
        )
        conn.commit()

        # Fetch updated record
        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (cleaned_id,))
        updated_row = cursor.fetchone()
        return dict(updated_row)
    finally:
        conn.close()
