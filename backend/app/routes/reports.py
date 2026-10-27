"""
Citizen Flood & SOS Report Routes
Handles report submission with input validation, cryptographic tracking ID generation,
and secure parameterized SQLite database operations.
"""

from typing import List, Optional
from datetime import datetime, timezone
import logging
import secrets
import sqlite3
from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_db_connection
from app.schemas import ReportCreate, ReportResponse, SeverityLevel, ReportStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def generate_report_id() -> str:
    """
    Generates a unique, collision-resistant tracking ID.
    Format: FL-XXXXXXXX (e.g., FL-A4C1B83D)
    Uses Python's secrets module for cryptographic randomness.
    """
    return f"FL-{secrets.token_hex(4).upper()}"


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen flood or emergency SOS report",
    description="Validates citizen input, assigns a unique tracking ID, stores the record in SQLite, and returns the created report.",
)
def create_report(payload: ReportCreate):
    """
    Submits a new emergency flood report.
    - Status defaults to 'Pending'
    - Timestamps are recorded in UTC ISO 8601 format
    - Uses parameterized SQL INSERT to guarantee SQL Injection immunity
    """
    report_id = generate_report_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (
                report_id, citizen_name, location, description, severity, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?);
            """,
            (
                report_id,
                payload.citizen_name,
                payload.location,
                payload.description,
                payload.severity.value,
                now_iso,
                now_iso,
            ),
        )
        conn.commit()

        # Retrieve the newly inserted report
        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (report_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Report creation could not be verified in database.",
            )

        return dict(row)

    except sqlite3.IntegrityError as e:
        logger.error(f"Database integrity error during report creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create report due to a database constraint conflict. Please retry.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during report creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while processing the emergency report.",
        )
    finally:
        conn.close()


@router.get(
    "",
    response_model=List[ReportResponse],
    summary="List all flood reports with optional filters",
    description="Returns a paginated list of flood reports, filterable by severity, status, or free-text search.",
)
def list_reports(
    severity: Optional[SeverityLevel] = None,
    status_filter: Optional[ReportStatus] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    Retrieves reports using parameterized query construction to ensure SQL injection safety.
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
            query += " AND (location LIKE ? OR description LIKE ? OR citizen_name LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Track a report by its unique tracking ID",
    description="Allows citizens to check the current status and rescue updates of their emergency request.",
)
def get_report_by_id(report_id: str):
    """
    Finds a single report by its tracking ID (e.g., FL-A89D2F).
    Returns 404 Not Found if the report does not exist.
    """
    cleaned_id = report_id.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE report_id = ?;", (cleaned_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with tracking ID '{cleaned_id}' was not found.",
            )

        return dict(row)
    finally:
        conn.close()

