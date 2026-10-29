"""Endpoint autentikasi admin."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import one
from ..schemas import LoginPayload, envelope
from ..security import current_admin, sign_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginPayload) -> dict:
    admin = one("SELECT * FROM admins WHERE LOWER(email) = LOWER(%s)", (str(payload.email),))
    if not admin or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah.")
    token = sign_token({"id": admin["id"], "email": admin["email"], "name": admin["name"]})
    return envelope({"token": token, "admin": {"id": admin["id"], "email": admin["email"], "name": admin["name"]}})


@router.get("/me")
def me(admin: dict = Depends(current_admin)) -> dict:
    return envelope({"id": admin["id"], "email": admin["email"], "name": admin["name"]})
