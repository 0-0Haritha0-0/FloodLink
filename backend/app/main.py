"""
FloodLink - Real-Time Flood Disaster Management & Emergency Response Platform
Aligns with:
  - SDG 11: Sustainable Cities and Communities
  - SDG 13: Climate Action

FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import init_db, get_db_connection
from app.routes import reports, auth, admin, rescue

# Load environment variables from a .env file if present
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Executes automatic database initialization when the server starts up.
    """
    init_db()
    yield


# Initialize FastAPI instance with descriptive metadata
app = FastAPI(
    title="FloodLink Emergency Response API",
    description="A platform for flood incident reporting, emergency response coordination, and disaster management.",
    version="1.0.0",
    lifespan=lifespan,
)

# Read allowed origins for CORS. Default to Vite's local dev server.
# Cybersecurity note: Avoid allowing wildcard '*' in production to prevent Cross-Origin data leaks.
origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """
    Root endpoint providing basic API details and documentation links.
    """
    return {
        "project": "FloodLink",
        "description": "Disaster Management & Emergency Response Platform",
        "version": "1.0.0",
        "sdg_goals": [
            "SDG 11: Sustainable Cities and Communities",
            "SDG 13: Climate Action",
        ],
        "docs_url": "/docs",
        "health_check": "/api/health",
    }


@app.get("/api/health")
def health_check():
    """
    Health check endpoint to verify backend operational readiness.
    Useful for uptime monitors, container orchestrators, and testing connectivity.
    """
    db_status = "connected"
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1;").fetchone()
        conn.close()
    except Exception as e:
        db_status = f"unavailable: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "service": "FloodLink Backend",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sdg_alignment": [
            "SDG 11: Sustainable Cities and Communities",
            "SDG 13: Climate Action",
        ],
        "environment": os.getenv("APP_ENV", "development"),
    }


# Include modular routers
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(rescue.router)

