"""Utilitas keamanan: hash password, token sesi, dan dependency auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Header, HTTPException, status

from .config import settings

TOKEN_TTL_MS = 12 * 60 * 60 * 1000
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 64


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_LEN,
    )
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=SCRYPT_LEN,
        )
        return hmac.compare_digest(candidate.hex(), digest)
    except (ValueError, TypeError):
        return False


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign_token(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body["exp"] = int(time.time() * 1000) + TOKEN_TTL_MS
    encoded = _b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.session_secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256
    ).digest()
    return f"{encoded}.{_b64encode(signature)}"


def verify_token(token: str) -> dict[str, Any] | None:
    try:
        encoded, signature = token.split(".")
        expected = hmac.new(
            settings.session_secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            return None
        payload = json.loads(_b64decode(encoded))
        if int(payload.get("exp", 0)) <= int(time.time() * 1000):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def random_code(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4).upper()}"


def current_admin(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    payload = verify_token(token) if token else None
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak valid.",
        )
    return payload
