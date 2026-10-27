"""
Authentication & Authorization Routes
Provides endpoints for login, session status, and logout with secure token management.
"""

from fastapi import APIRouter, HTTPException, Depends, status

from app.database import get_db_connection
from app.schemas import AdminLogin, TokenResponse, UserProfile
from app.auth import (
    verify_password,
    create_session_token,
    revoke_session_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate admin or rescue personnel",
    description="Validates username & password against salted PBKDF2 hash and returns an access token.",
)
def login(payload: AdminLogin):
    """
    Authenticates a user and generates an active session token.
    Enforces secure constant-time hash comparison to prevent timing attacks.
    """
    username = payload.username.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, password_hash, role FROM admins WHERE username = ?;",
            (username,),
        )
        user = cursor.fetchone()

        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials. Please verify username and password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_session_token(username=user["username"], role=user["role"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user["username"],
            "role": user["role"],
        }
    finally:
        conn.close()


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current authenticated user profile",
    description="Validates Bearer token and returns user details.",
)
def get_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns profile information for the authenticated token.
    """
    return {
        "username": current_user["username"],
        "role": current_user["role"],
    }


@router.post(
    "/logout",
    summary="Revoke active authentication token",
    description="Invalidates current session token in the database.",
)
def logout(current_user: dict = Depends(get_current_user)):
    """
    Deletes the current user's session token.
    """
    revoked = revoke_session_token(current_user["token"])
    return {"message": "Logged out successfully.", "revoked": revoked}
