"""
Rescue Team Workflow Routes
Dedicated endpoints for rescue personnel in the field:
  - View assigned emergency incidents
  - Update on-ground operational status
  - Record rescue progress notes and mark incidents Resolved
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db_connection
from app.schemas import ReportResponse, RescueProgressUpdate, ReportStatus
from app.auth import require_role

router = APIRouter(
    prefix="/api/rescue",
    tags=["rescue"],
    dependencies=[Depends(require_role(["rescue_team", "admin"]))],
)

STANDARD_RESCUE_TEAMS = [
    {"id": "team-boat-alpha", "name": "Team Alpha — Rapid Boat Rescue", "specialty": "Water Evacuation"},
    {"id": "team-med-beta", "name": "Team Beta — Emergency Medical Response", "specialty": "First Aid & Triage"},
    {"id": "team-evac-gamma", "name": "Team Charlie — High-Ground Evacuation", "specialty": "Transport & Shelters"},
    {"id": "team-supply-delta", "name": "Team Delta — Food & Relief Logistics", "specialty": "Supply Delivery"},
]


@router.get(
    "/teams",
    summary="List available emergency rescue teams",
    description="Returns standard dispatched rescue squads available for assignment.",
)
def get_rescue_teams():
    """
    Returns available emergency rescue teams.
    """
    return STANDARD_RESCUE_TEAMS


@router.get(
    "/assignments",
    response_model=List[ReportResponse],
    summary="List incidents assigned to rescue teams",
    description="Retrieves active incidents assigned to rescue units for dispatch and triage.",
)
def get_rescue_assignments(
    team_name: Optional[str] = None,
):
    """
    Retrieves reports with status 'Assigned' or 'In Progress' for field rescue operations.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if team_name and team_name.strip():
            cursor.execute(
                """
                SELECT * FROM reports
                WHERE assigned_team = ? AND status != 'Resolved'
                ORDER BY CASE severity
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END ASC, id DESC;
                """,
                (team_name.strip(),),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM reports
                WHERE assigned_team IS NOT NULL AND status != 'Resolved'
                ORDER BY CASE severity
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END ASC, id DESC;
                """
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@router.patch(
    "/reports/{report_id}/progress",
    response_model=ReportResponse,
    summary="Update rescue progress and mark resolved",
    description="Allows rescue operators to report situation updates and resolve emergencies.",
)
def update_rescue_progress(report_id: str, payload: RescueProgressUpdate):
    """
    Updates status to 'In Progress' or 'Resolved' and appends rescue operational log.
    """
    cleaned_id = report_id.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Rescue teams can only update to 'In Progress' or 'Resolved'
    if payload.status not in (ReportStatus.IN_PROGRESS, ReportStatus.RESOLVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rescue teams can only update status to 'In Progress' or 'Resolved'.",
        )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (cleaned_id,))
        existing = cursor.fetchone()

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with tracking ID '{cleaned_id}' not found.",
            )

        # Append progress notes with timestamp
        existing_notes = existing["admin_notes"] or ""
        log_entry = f"[{now_iso[:19]} UTC - RESCUE]: {payload.progress_notes.strip()}"
        combined_notes = f"{existing_notes}\n{log_entry}".strip() if existing_notes else log_entry

        cursor.execute(
            """
            UPDATE reports
            SET status = ?, admin_notes = ?, updated_at = ?
            WHERE report_id = ?;
            """,
            (payload.status.value, combined_notes, now_iso, cleaned_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (cleaned_id,))
        return dict(cursor.fetchone())
    finally:
        conn.close()
