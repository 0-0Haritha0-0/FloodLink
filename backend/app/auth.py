"""
FloodLink Authentication & Password Hashing Security Module
Implements:
  - NIST-recommended PBKDF2-HMAC-SHA256 password hashing with random salt
  - Constant-time hash verification via hmac.compare_digest (prevents timing attacks)
  - Cryptographically secure session token generation
  - SQLite persistent token verification
  - FastAPI dependency injection for role-based access control (RBAC)
"""

from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import os
import secrets
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db_connection

# HTTP Bearer authentication scheme
security_scheme = HTTPBearer(auto_error=False)

TOKEN_EXPIRATION_HOURS = 24
PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with a unique 16-byte random salt.
    Returns format: '<salt_hex>$<hash_hex>'
    """
    salt = secrets.token_bytes(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored '<salt_hex>$<hash_hex>' string.
    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    try:
        salt_hex, hash_hex = stored_hash.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False


def create_session_token(username: str, role: str) -> str:
    """
    Generates a cryptographically secure 256-bit token and stores it in SQLite active_tokens.
    """
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=TOKEN_EXPIRATION_HOURS)

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO active_tokens (token, username, role, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (token, username, role, expires_at.isoformat(), now.isoformat()),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def revoke_session_token(token: str) -> bool:
    """
    Deletes a session token from the active_tokens table.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_tokens WHERE token = ?;", (token,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency: Validates the Bearer token against active SQLite sessions.
    Raises HTTP 401 Unauthorized if missing, expired, or invalid.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials.strip()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT token, username, role, expires_at FROM active_tokens WHERE token = ?;",
            (token,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Clean up expired token
            conn.execute("DELETE FROM active_tokens WHERE token = ?;", (token,))
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "token": row["token"],
            "username": row["username"],
            "role": row["role"],
        }
    finally:
        conn.close()


def require_role(allowed_roles: list[str]):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Example: Depends(require_role(["admin"]))
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of these roles: {allowed_roles}",
            )
        return current_user

    return role_checker
