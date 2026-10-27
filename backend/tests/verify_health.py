"""
Verification script for Stage 2: FastAPI Setup and Health Check
Tests the endpoint functions and application configuration directly.
"""

import os
import sys

# Ensure backend directory is in the import search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, health_check, read_root


def test_app_configuration():
    """Verifies FastAPI application metadata."""
    print("1. Checking application configuration...")
    assert app.title == "FloodLink Emergency Response API"
    assert app.version == "1.0.0"
    print("   [OK] App title and version verified.")


def test_root_endpoint():
    """Verifies the root endpoint response structure."""
    print("\n2. Testing root endpoint `read_root()`...")
    response = read_root()
    assert response["project"] == "FloodLink"
    assert response["version"] == "1.0.0"
    assert "SDG 11: Sustainable Cities and Communities" in response["sdg_goals"]
    assert "SDG 13: Climate Action" in response["sdg_goals"]
    assert response["health_check"] == "/api/health"
    print("   [OK] Root response:", response)


def test_health_check_endpoint():
    """Verifies the health check endpoint response structure and fields."""
    print("\n3. Testing health check endpoint `health_check()`...")
    response = health_check()
    assert response["status"] == "healthy"
    assert response["service"] == "FloodLink Backend"
    assert "timestamp_utc" in response
    assert "SDG 11: Sustainable Cities and Communities" in response["sdg_alignment"]
    assert "SDG 13: Climate Action" in response["sdg_alignment"]
    print("   [OK] Health check response:", response)


if __name__ == "__main__":
    print("=" * 60)
    print("Running FloodLink Stage 2 Verification Tests")
    print("=" * 60)
    test_app_configuration()
    test_root_endpoint()
    test_health_check_endpoint()
    print("\n" + "=" * 60)
    print("STAGE 2 VERIFICATION SUCCESSFUL: All tests passed!")
    print("=" * 60)
