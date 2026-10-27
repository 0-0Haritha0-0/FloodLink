"""
Comprehensive Stage 2 Test Suite
Tests:
  1. Python & Pydantic 2.13.4 environment verification
  2. Request/Response schemas import and strict validation rules
  3. FastAPI application startup and route registration
  4. Root endpoint (/) output and metadata
  5. /api/health endpoint output, status, and SDG alignment
"""

import os
import sys
import pydantic

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, read_root, health_check
from app.schemas import (
    ReportCreate,
    ReportResponse,
    ReportStatusUpdate,
    AdminLogin,
    SeverityLevel,
    ReportStatus,
)


def test_pydantic_version():
    """Verify that Pydantic version 2.13.4 is present."""
    print("[1] Verifying Pydantic version...")
    actual_version = pydantic.__version__
    print(f"    Detected Pydantic version: {actual_version}")
    assert actual_version == "2.13.4", f"Expected 2.13.4, got {actual_version}"
    print("    [PASS] Pydantic 2.13.4 verified.")


def test_schemas_validation():
    """Verify that request/response schemas validate correctly and reject invalid input."""
    print("\n[2] Testing Pydantic request & response schemas...")

    # A. Valid ReportCreate submission
    valid_data = {
        "citizen_name": "  Aditi Sharma  ",  # Tests auto-stripping
        "location": "Near Central Hospital, Ward 4",
        "description": "Flash flood waters entered ground floor. 4 people need evacuation.",
        "severity": "Critical",
    }
    report = ReportCreate(**valid_data)
    assert report.citizen_name == "Aditi Sharma", "Expected whitespace stripping"
    assert report.severity == SeverityLevel.CRITICAL
    print("    [PASS] Valid ReportCreate serialized successfully.")

    # B. Invalid severity rejection (Gateway firewall test)
    try:
        ReportCreate(
            citizen_name="Aditi",
            location="Ward 4",
            description="Water is high",
            severity="INVALID_SEVERITY_LEVEL",  # Should trigger ValidationError
        )
        assert False, "Should have raised a ValidationError for invalid severity"
    except pydantic.ValidationError as e:
        print("    [PASS] Invalid severity was correctly rejected by schema.")

    # C. Empty whitespace rejection
    try:
        ReportCreate(
            citizen_name="   ",  # Invalid empty name
            location="Ward 4",
            description="Flooding",
            severity="High",
        )
        assert False, "Should have raised a ValidationError for empty name"
    except pydantic.ValidationError:
        print("    [PASS] Whitespace-only input was correctly rejected.")

    # D. Test AdminLogin schema
    admin = AdminLogin(username="  admin_user  ", password="SecurePassword123")
    assert admin.username == "admin_user"
    print("    [PASS] AdminLogin schema validated successfully.")


def test_fastapi_app_startup():
    """Verify FastAPI application instance and registered routes."""
    print("\n[3] Testing FastAPI application instance & routing table...")
    assert app.title == "FloodLink Emergency Response API"
    assert app.version == "1.0.0"

    # Inspect registered routes in the FastAPI routing table
    routes = {}
    for route in app.routes:
        if hasattr(route, "path"):
            routes[route.path] = route.name
        elif hasattr(route, "original_router"):
            for sub_route in route.original_router.routes:
                if hasattr(sub_route, "path"):
                    routes[sub_route.path] = sub_route.name

    print(f"    Registered routes in app: {list(routes.keys())}")

    assert "/" in routes, "Root endpoint '/' must be registered"
    assert "/api/health" in routes, "Health endpoint '/api/health' must be registered"
    assert "/docs" in routes, "OpenAPI Swagger docs endpoint '/docs' must be registered"
    assert "/openapi.json" in routes, "OpenAPI schema '/openapi.json' must be registered"
    print("    [PASS] FastAPI application started and routes registered cleanly.")


def test_root_endpoint():
    """Verify root GET / endpoint."""
    print("\n[4] Testing GET / endpoint...")
    result = read_root()
    assert result["project"] == "FloodLink"
    assert result["version"] == "1.0.0"
    assert "SDG 11: Sustainable Cities and Communities" in result["sdg_goals"]
    assert "SDG 13: Climate Action" in result["sdg_goals"]
    print("    [PASS] Root endpoint returned valid response:")
    print(f"           {result}")


def test_health_endpoint():
    """Verify GET /api/health endpoint."""
    print("\n[5] Testing GET /api/health endpoint...")
    result = health_check()
    assert result["status"] == "healthy"
    assert result["service"] == "FloodLink Backend"
    assert "timestamp_utc" in result
    assert "SDG 11: Sustainable Cities and Communities" in result["sdg_alignment"]
    assert "SDG 13: Climate Action" in result["sdg_alignment"]
    print("    [PASS] Health check returned valid status:")
    print(f"           {result}")


if __name__ == "__main__":
    print("=" * 65)
    print("FLOODLINK STAGE 2 COMPREHENSIVE TEST SUITE")
    print("=" * 65)
    test_pydantic_version()
    test_schemas_validation()
    test_fastapi_app_startup()
    test_root_endpoint()
    test_health_endpoint()
    print("=" * 65)
    print("TEST SUITE COMPLETED: 5/5 CHECKS PASSED WITH 0 ERRORS")
    print("=" * 65)
