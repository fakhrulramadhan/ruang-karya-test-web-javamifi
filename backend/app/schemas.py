"""Skema request/response API."""

from __future__ import annotations

from datetime import date as DateType
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class OrderPayload(BaseModel):
    workshopId: int = Field(gt=0)
    customerName: str = Field(min_length=2, max_length=100)
    customerEmail: EmailStr
    customerPhone: str = Field(min_length=6, max_length=30)
    quantity: int = Field(ge=1, le=8)

    @field_validator("customerName", "customerPhone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Tidak boleh kosong.")
        return cleaned


class WorkshopCreate(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    category: str = Field(min_length=2, max_length=50)
    location: str = Field(min_length=2, max_length=80)
    date: DateType
    time: str = Field(min_length=3, max_length=40)
    price: int = Field(ge=0, le=100_000_000)
    capacity: int = Field(ge=1, le=500)
    description: str = Field(min_length=10, max_length=2000)
    image: str | None = Field(default=None, max_length=500)
    featured: bool = False
    status: Literal["draft", "published", "archived"] = "published"


class WorkshopUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    location: str | None = Field(default=None, min_length=2, max_length=80)
    date: DateType | None = None
    time: str | None = Field(default=None, min_length=3, max_length=40)
    price: int | None = Field(default=None, ge=0, le=100_000_000)
    capacity: int | None = Field(default=None, ge=1, le=500)
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    image: str | None = Field(default=None, max_length=500)
    featured: bool | None = None
    status: Literal["draft", "published", "archived"] | None = None


class PaymentNotification(BaseModel):
    order_id: str | None = None
    transaction_id: str | None = None
    transaction_status: str | None = None
    fraud_status: str | None = None
    status_code: str | None = None
    gross_amount: str | None = None
    signature_key: str | None = None
    payment_type: str | None = None


def envelope(data: Any = None, message: str | None = None, meta: dict | None = None) -> dict:
    payload: dict[str, Any] = {"success": True}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    if meta:
        payload["meta"] = meta
    return payload
