"""Koneksi PostgreSQL, skema, dan data awal."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Sequence

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    open=False,
)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS admins (
        id BIGSERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workshops (
        id BIGSERIAL PRIMARY KEY,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        location TEXT NOT NULL,
        date DATE NOT NULL,
        time TEXT NOT NULL,
        price INTEGER NOT NULL CHECK (price >= 0),
        capacity INTEGER NOT NULL CHECK (capacity > 0),
        booked INTEGER NOT NULL DEFAULT 0 CHECK (booked >= 0),
        description TEXT NOT NULL,
        image TEXT NOT NULL,
        featured BOOLEAN NOT NULL DEFAULT FALSE,
        status TEXT NOT NULL DEFAULT 'published'
            CHECK (status IN ('draft', 'published', 'archived')),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id BIGSERIAL PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        workshop_id BIGINT NOT NULL REFERENCES workshops(id),
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        total INTEGER NOT NULL CHECK (total >= 0),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'paid', 'cancelled')),
        payment_ref TEXT,
        payment_provider TEXT NOT NULL DEFAULT 'mock',
        payment_url TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        paid_at TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_workshops_status_date ON workshops(status, date)",
    "CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at DESC)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_provider TEXT NOT NULL DEFAULT 'mock'",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_url TEXT",
)

SEED_WORKSHOPS: tuple[dict[str, Any], ...] = (
    {
        "slug": "membentuk-tanah",
        "title": "Membentuk Tanah",
        "category": "Keramik",
        "location": "Bandung",
        "date": "2026-11-14",
        "time": "10.00—13.00",
        "price": 425000,
        "capacity": 12,
        "description": "Eksplorasi bentuk, tekstur, dan ritme bersama perajin lokal. Tidak perlu pengalaman sebelumnya.",
        "image": "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=1200&q=80",
        "featured": True,
    },
    {
        "slug": "cetak-yang-bercerita",
        "title": "Cetak yang Bercerita",
        "category": "Cetak Saring",
        "location": "Yogyakarta",
        "date": "2026-11-21",
        "time": "14.00—17.00",
        "price": 350000,
        "capacity": 15,
        "description": "Kenali dasar cetak saring dan pulang membawa seri print buatanmu sendiri.",
        "image": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=1200&q=80",
        "featured": False,
    },
    {
        "slug": "mata-yang-peka",
        "title": "Mata yang Peka",
        "category": "Fotografi",
        "location": "Jakarta",
        "date": "2026-12-05",
        "time": "09.00—12.00",
        "price": 500000,
        "capacity": 10,
        "description": "Berjalan, mengamati, dan memotret kota dengan pendekatan yang lebih personal.",
        "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=1200&q=80",
        "featured": False,
    },
)


def open_pool() -> None:
    if pool.closed:
        pool.open(wait=True, timeout=15)


def close_pool() -> None:
    if not pool.closed:
        pool.close()


@contextmanager
def connection() -> Iterator[Any]:
    with pool.connection() as conn:
        yield conn


def query(sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description is None:
                return []
            return list(cur.fetchall())


def one(sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Sequence[Any] | None = None) -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())


def initialize_database() -> None:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)


def seed_workshops() -> None:
    existing = one("SELECT COUNT(*)::int AS count FROM workshops")
    if existing and existing["count"] > 0:
        return
    for row in SEED_WORKSHOPS:
        execute(
            """
            INSERT INTO workshops
                (slug, title, category, location, date, time, price, capacity, description, image, featured)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row["slug"],
                row["title"],
                row["category"],
                row["location"],
                row["date"],
                row["time"],
                row["price"],
                row["capacity"],
                row["description"],
                row["image"],
                row["featured"],
            ),
        )


def ensure_admin(email: str, password_hash: str, name: str) -> bool:
    existing = one("SELECT id FROM admins WHERE email = %s", (email,))
    if existing:
        return False
    execute(
        "INSERT INTO admins (email, password_hash, name) VALUES (%s, %s, %s)",
        (email, password_hash, name),
    )
    return True


def placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def build_in_clause(values: Iterable[Any]) -> tuple[str, list[Any]]:
    items = list(values)
    return placeholders(len(items)), items
