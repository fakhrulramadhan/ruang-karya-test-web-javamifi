"""Payment mock dan Midtrans Snap sandbox."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings
from ..database import one, query
from ..security import random_code

logger = logging.getLogger("ruangkarya.payment")


def payment_mode() -> str:
    return "midtrans" if settings.midtrans_enabled else "mock"


def _basic_auth() -> str:
    raw = f"{settings.midtrans_server_key}:".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


async def create_midtrans_transaction(order: dict[str, Any]) -> dict[str, Any]:
    """Buat transaksi Snap Midtrans dan kembalikan token/redirect URL."""
    if not settings.midtrans_enabled:
        raise RuntimeError("MIDTRANS_SERVER_KEY belum diatur.")
    payload = {
        "transaction_details": {
            "order_id": order["code"],
            "gross_amount": int(order["total"]),
        },
        "item_details": [
            {
                "id": str(order["workshop_id"]),
                "price": int(order["total"] // order["quantity"]),
                "quantity": int(order["quantity"]),
                "name": str(order.get("title", "Workshop Ruang Karya"))[:50],
            }
        ],
        "customer_details": {
            "first_name": order["customer_name"],
            "email": order["customer_email"],
            "phone": order["customer_phone"],
        },
        "expiry": {"unit": "minutes", "duration": settings.payment_expiry_minutes},
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {_basic_auth()}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.midtrans_snap_base}/transactions",
            headers=headers,
            json=payload,
        )
    if not response.is_success:
        logger.error("Midtrans create transaction %s: %s", response.status_code, response.text)
        raise RuntimeError("Midtrans menolak transaksi pembayaran.")
    result = response.json()
    return {
        "provider": "midtrans",
        "token": result.get("token"),
        "redirectUrl": result.get("redirect_url"),
        "clientKey": settings.midtrans_client_key,
        "snapScript": settings.midtrans_snap_script,
        "expiresAt": (
            datetime.now(timezone.utc) + timedelta(minutes=settings.payment_expiry_minutes)
        ).isoformat(),
    }


def create_mock_payment(order: dict[str, Any]) -> dict[str, Any]:
    payment_ref = random_code("PAY")
    signature = hashlib.sha256(
        f"{order['code']}:{order['total']}:{payment_ref}:ruang-karya".encode("utf-8")
    ).hexdigest()
    return {
        "provider": "mock",
        "paymentRef": payment_ref,
        "signature": signature,
        "amount": order["total"],
        "expiresAt": (
            datetime.now(timezone.utc) + timedelta(minutes=settings.payment_expiry_minutes)
        ).isoformat(),
        "instructions": [
            "Pilih metode pembayaran simulasi di bawah.",
            "Klik Konfirmasi Pembayaran untuk menyelesaikan pesanan.",
            "Status akan langsung berubah menjadi lunas.",
        ],
    }


def create_payment(order: dict[str, Any]) -> dict[str, Any]:
    """Payload awal yang dipakai frontend; Midtrans dibuat async di service route."""
    return create_mock_payment(order) if payment_mode() == "mock" else {
        "provider": "midtrans",
        "clientKey": settings.midtrans_client_key,
        "expiresAt": (
            datetime.now(timezone.utc) + timedelta(minutes=settings.payment_expiry_minutes)
        ).isoformat(),
    }


def is_successful_notification(payload: dict[str, Any]) -> bool:
    status = (payload.get("transaction_status") or "").lower()
    fraud = (payload.get("fraud_status") or "accept").lower()
    return status in {"capture", "settlement"} and fraud in {"accept", ""}


def verify_midtrans_signature(payload: dict[str, Any]) -> bool:
    if not settings.midtrans_server_key:
        return False
    source = (
        f"{payload.get('order_id', '')}"
        f"{payload.get('status_code', '')}"
        f"{payload.get('gross_amount', '')}"
        f"{settings.midtrans_server_key}"
    )
    expected = hashlib.sha512(source.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, str(payload.get("signature_key", "")))


def find_order_by_code(code: str) -> dict[str, Any] | None:
    return one(
        """
        SELECT o.*, w.title, w.date, w.time, w.location, w.image
        FROM orders o JOIN workshops w ON w.id = o.workshop_id WHERE o.code = %s
        """,
        (code,),
    )


def update_order_paid(code: str, payment_ref: str | None = None) -> dict[str, Any] | None:
    rows = query(
        """
        UPDATE orders
        SET status = 'paid', payment_ref = COALESCE(%s, payment_ref, %s), paid_at = NOW()
        WHERE code = %s AND status <> 'paid'
        RETURNING *
        """,
        (payment_ref, random_code("PAY"), code),
    )
    return rows[0] if rows else find_order_by_code(code)
