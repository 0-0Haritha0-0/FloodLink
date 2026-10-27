"""
Pydantic schemas for data validation and serialization.
Compatible with Pydantic v2 (Pydantic 2.13.4).

Cybersecurity & Quality Features:
- Strict field validation prevents empty/whitespace-only input.
- String length limits prevent denial-of-service via huge payloads.
- Enums enforce valid severities and statuses at the API gateway level.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ReportStatus(str, Enum):
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class ReportCreate(BaseModel):
    """
    Schema for citizen flood/SOS report submissions.
    """
    citizen_name: str = Field(..., min_length=2, max_length=100, description="Name of citizen or reporter")
    location: str = Field(..., min_length=3, max_length=255, description="Street, landmark, or area name")
    description: str = Field(..., min_length=5, max_length=1000, description="Description of the flood situation")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="Urgency/severity level")

    @field_validator("citizen_name", "location", "description")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or just whitespace.")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "citizen_name": "Jane Doe",
                "location": "Near River Bridge, Ward 7",
                "description": "Water rising above waist level, 3 people stranded on first floor.",
                "severity": "Critical",
            }
        }
    )


class ReportStatusUpdate(BaseModel):
    """
    Schema for admin/rescue team to update status or assignment.
    """
    status: ReportStatus = Field(..., description="Updated status of the emergency response")
    assigned_team: Optional[str] = Field(None, max_length=100, description="Name of the rescue team assigned")
    admin_notes: Optional[str] = Field(None, max_length=500, description="Internal coordination notes")

    @field_validator("assigned_team", "admin_notes")
    @classmethod
    def strip_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class ReportResponse(BaseModel):
    """
    Schema for reports returned to citizen, admin, and rescue dashboard.
    """
    id: int = Field(..., description="Internal database integer ID")
    report_id: str = Field(..., description="Unique human-readable tracking ID (e.g. FL-A89D2F)")
    citizen_name: str
    location: str
    description: str
    severity: SeverityLevel
    status: ReportStatus
    assigned_team: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class AdminLogin(BaseModel):
    """
    Schema for admin authentication credentials.
    """
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()


class TokenResponse(BaseModel):
    """
    Schema for successful authentication response.
    """
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserProfile(BaseModel):
    """
    Schema for authenticated user profile info.
    """
    username: str
    role: str


class RescueProgressUpdate(BaseModel):
    """
    Schema for rescue teams updating incident status and rescue progress.
    """
    status: ReportStatus = Field(..., description="Target status: 'In Progress' or 'Resolved'")
    progress_notes: str = Field(..., min_length=2, max_length=500, description="Notes on rescue action taken")

    @field_validator("progress_notes")
    @classmethod
    def strip_notes(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Progress notes cannot be empty.")
        return stripped


class AdminStats(BaseModel):
    """
    Incident KPI statistics for management dashboard.
    """
    total_reports: int
    pending: int
    assigned: int
    in_progress: int
    resolved: int
    critical_unresolved: int

