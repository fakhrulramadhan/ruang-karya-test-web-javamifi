"""Endpoint publik dan CMS."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..config import settings
from ..database import connection, one, query
from ..schemas import (
    OrderPayload,
    PaymentNotification,
    WorkshopCreate,
    WorkshopUpdate,
    envelope,
)
from ..security import current_admin, random_code
from ..services import payment as payment_service
from ..services.external import (
    fetch_exchange_rate,
    get_cached_rate,
    notify_n8n,
    refresh_rate_in_background,
)

logger = logging.getLogger("ruangkarya.api")

router = APIRouter(prefix="/api", tags=["api"])

WORKSHOP_SELECT = "SELECT *, capacity - booked AS available FROM workshops"


def _slugify(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in " -" else "" for ch in value.lower())
    return "-".join(cleaned.split())[:80] or random_code("WS").lower()


def _unique_slug(base: str, exclude_id: int | None = None) -> str:
    slug = base
    counter = 2
    while True:
        existing = one("SELECT id FROM workshops WHERE slug = %s", (slug,))
        if not existing or (exclude_id and existing["id"] == exclude_id):
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _workshop_or_404(workshop_id: int) -> dict[str, Any]:
    row = one(f"{WORKSHOP_SELECT} WHERE id = %s", (workshop_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop tidak ditemukan.")
    return row


@router.get("/health")
def health() -> dict:
    return envelope(
        {
            "service": "ruang-karya-api",
            "status": "ok",
            "database": "postgresql",
            "runtime": "python-fastapi",
            "paymentMode": payment_service.payment_mode(),
        }
    )


@router.get("/config")
def public_config() -> dict:
    return envelope(
        {
            "paymentMode": payment_service.payment_mode(),
            "midtransClientKey": settings.midtrans_client_key if settings.midtrans_enabled else "",
            "midtransSnapScript": settings.midtrans_snap_script if settings.midtrans_enabled else "",
            "midtransProduction": settings.midtrans_production,
        }
    )


@router.get("/workshops")
def list_workshops(
    category: str | None = Query(default=None, max_length=50),
    q: str | None = Query(default=None, max_length=80),
) -> dict:
    conditions = ["status = 'published'"]
    params: list[Any] = []
    if category:
        params.append(category)
        conditions.append(f"category = %s")
    if q:
        params.append(f"%{q.lower()}%")
        conditions.append(
            f"LOWER(title || ' ' || category || ' ' || location) LIKE %s"
        )
    rows = query(
        f"{WORKSHOP_SELECT} WHERE {' AND '.join(conditions)} ORDER BY featured DESC, date ASC",
        params,
    )
    refresh_rate_in_background()
    return envelope(rows, meta={"exchangeRateUSD": get_cached_rate()})


@router.get("/workshops/{slug}")
def workshop_detail(slug: str) -> dict:
    row = one(f"{WORKSHOP_SELECT} WHERE slug = %s", (slug,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop tidak ditemukan.")
    return envelope(row)


@router.get("/exchange-rate")
async def exchange_rate() -> dict:
    rate = await fetch_exchange_rate()
    return envelope({"base": "IDR", "quote": "USD", "rate": rate})


@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderPayload) -> dict:
    workshop = one(
        f"{WORKSHOP_SELECT} WHERE id = %s AND status = 'published'", (payload.workshopId,)
    )
    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop tidak tersedia.")
    if payload.quantity > workshop["available"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Sisa kursi tidak mencukupi."
        )

    code = random_code("RK")
    total = int(workshop["price"]) * payload.quantity
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders
                    (code, workshop_id, customer_name, customer_email, customer_phone,
                     quantity, total, payment_provider)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    code,
                    workshop["id"],
                    payload.customerName,
                    str(payload.customerEmail),
                    payload.customerPhone,
                    payload.quantity,
                    total,
                    payment_service.payment_mode(),
                ),
            )

    order = one(
        """
        SELECT o.*, w.title, w.date, w.time, w.location, w.image
        FROM orders o JOIN workshops w ON w.id = o.workshop_id WHERE o.code = %s
        """,
        (code,),
    )
    payment = payment_service.create_payment(order)
    if payment["provider"] == "midtrans":
        try:
            snap = await payment_service.create_midtrans_transaction(order)
            payment.update(snap)
            query(
                "UPDATE orders SET payment_ref = %s, payment_url = %s WHERE code = %s",
                (snap.get("token"), snap.get("redirectUrl"), code),
            )
        except Exception as error:  # noqa: BLE001 - pesanan tetap dibuat
            logger.error("Gagal membuat transaksi Midtrans: %s", error)
            payment["error"] = "Transaksi Midtrans gagal dibuat, gunakan mode mock."
    return envelope({"order": order, "payment": payment})


@router.post("/orders/{code}/pay")
async def pay_order(code: str) -> dict:
    order = one("SELECT * FROM orders WHERE code = %s", (code,))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")
    if order["status"] == "paid":
        return envelope(payment_service.find_order_by_code(code))

    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM workshops WHERE id = %s FOR UPDATE", (order["workshop_id"],))
            locked = cur.fetchone()
            if not locked or locked["capacity"] - locked["booked"] < order["quantity"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Kursi sudah tidak tersedia."
                )
            cur.execute(
                """
                UPDATE orders SET status = 'paid', payment_ref = COALESCE(payment_ref, %s), paid_at = NOW()
                WHERE code = %s
                """,
                (random_code("PAY"), code),
            )
            cur.execute(
                "UPDATE workshops SET booked = booked + %s WHERE id = %s",
                (order["quantity"], order["workshop_id"]),
            )

    paid = payment_service.find_order_by_code(code)
    await notify_n8n({"event": "order.paid", "order": paid})
    return envelope(paid)


@router.get("/orders/{code}")
def order_detail(code: str) -> dict:
    order = payment_service.find_order_by_code(code)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")
    return envelope(order)


@router.post("/payments/midtrans/notification")
async def midtrans_notification(payload: PaymentNotification, request: Request) -> dict:
    body = payload.model_dump()
    if not payment_service.verify_midtrans_signature(body):
        logger.warning("Signature Midtrans tidak valid untuk %s", body.get("order_id"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature tidak valid.")

    code = str(body.get("order_id") or "")
    order = one("SELECT * FROM orders WHERE code = %s", (code,))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")

    if payment_service.is_successful_notification(body):
        if order["status"] != "paid":
            with connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM workshops WHERE id = %s FOR UPDATE", (order["workshop_id"],)
                    )
                    locked = cur.fetchone()
                    if locked and locked["capacity"] - locked["booked"] >= order["quantity"]:
                        cur.execute(
                            """
                            UPDATE orders SET status = 'paid', payment_ref = %s, paid_at = NOW()
                            WHERE code = %s
                            """,
                            (body.get("transaction_id") or random_code("PAY"), code),
                        )
                        cur.execute(
                            "UPDATE workshops SET booked = booked + %s WHERE id = %s",
                            (order["quantity"], order["workshop_id"]),
                        )
            paid = payment_service.find_order_by_code(code)
            await notify_n8n({"event": "order.paid", "order": paid, "source": "midtrans"})
    elif (body.get("transaction_status") or "").lower() in {"deny", "cancel", "expire"}:
        query("UPDATE orders SET status = 'cancelled' WHERE code = %s AND status = 'pending'", (code,))

    return envelope({"received": True})


@router.get("/admin/stats")
def admin_stats(admin: dict = Depends(current_admin)) -> dict:
    workshops = one("SELECT COUNT(*)::int AS n FROM workshops WHERE status = 'published'")
    orders = one("SELECT COUNT(*)::int AS n FROM orders")
    revenue = one("SELECT COALESCE(SUM(total), 0)::int AS n FROM orders WHERE status = 'paid'")
    attendees = one("SELECT COALESCE(SUM(quantity), 0)::int AS n FROM orders WHERE status = 'paid'")
    return envelope(
        {
            "workshops": workshops["n"],
            "orders": orders["n"],
            "revenue": revenue["n"],
            "attendees": attendees["n"],
        }
    )


@router.get("/admin/workshops")
def admin_workshops(admin: dict = Depends(current_admin)) -> dict:
    return envelope(query(f"{WORKSHOP_SELECT} ORDER BY date DESC"))


@router.get("/admin/orders")
def admin_orders(admin: dict = Depends(current_admin)) -> dict:
    return envelope(
        query(
            """
            SELECT o.*, w.title FROM orders o JOIN workshops w ON w.id = o.workshop_id
            ORDER BY o.created_at DESC
            """
        )
    )


@router.post("/admin/workshops", status_code=status.HTTP_201_CREATED)
def create_workshop(payload: WorkshopCreate, admin: dict = Depends(current_admin)) -> dict:
    slug = _unique_slug(_slugify(payload.title))
    image = payload.image or (
        "https://images.unsplash.com/photo-1513364776144-60967b0f800f"
        "?auto=format&fit=crop&w=1200&q=80"
    )
    rows = query(
        """
        INSERT INTO workshops
            (slug, title, category, location, date, time, price, capacity, description, image, featured, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *, capacity - booked AS available
        """,
        (
            slug,
            payload.title.strip(),
            payload.category.strip(),
            payload.location.strip(),
            payload.date,
            payload.time.strip(),
            payload.price,
            payload.capacity,
            payload.description.strip(),
            image,
            payload.featured,
            payload.status,
        ),
    )
    return envelope(rows[0])


@router.patch("/admin/workshops/{workshop_id}")
def update_workshop(
    workshop_id: int, payload: WorkshopUpdate, admin: dict = Depends(current_admin)
) -> dict:
    _workshop_or_404(workshop_id)
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        return envelope(_workshop_or_404(workshop_id))

    if "title" in data:
        data["slug"] = _unique_slug(_slugify(data["title"]), exclude_id=workshop_id)
    if "capacity" in data:
        current = _workshop_or_404(workshop_id)
        if data["capacity"] < current["booked"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Kapasitas tidak boleh lebih kecil dari kursi terisi ({current['booked']}).",
            )

    assignments = ", ".join(f"{column} = %s" for column in data)
    values = list(data.values()) + [workshop_id]
    rows = query(
        f"UPDATE workshops SET {assignments} WHERE id = %s RETURNING *, capacity - booked AS available",
        values,
    )
    return envelope(rows[0])


@router.delete("/admin/workshops/{workshop_id}")
def delete_workshop(workshop_id: int, admin: dict = Depends(current_admin)) -> dict:
    workshop = _workshop_or_404(workshop_id)
    used = one("SELECT COUNT(*)::int AS n FROM orders WHERE workshop_id = %s", (workshop_id,))
    if used and used["n"] > 0:
        query("UPDATE workshops SET status = 'archived' WHERE id = %s", (workshop_id,))
        return envelope({"id": workshop_id, "status": "archived"}, message="Workshop diarsipkan karena sudah memiliki pesanan.")
    query("DELETE FROM workshops WHERE id = %s", (workshop_id,))
    return envelope({"id": workshop_id, "deleted": True}, message="Workshop dihapus.")
