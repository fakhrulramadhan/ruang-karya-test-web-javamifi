"""Seed database PostgreSQL dan akun admin awal."""

from __future__ import annotations

from app.config import settings
from app.database import (
    close_pool,
    ensure_admin,
    initialize_database,
    one,
    open_pool,
    seed_workshops,
)
from app.security import hash_password


def main() -> None:
    open_pool()
    try:
        initialize_database()
        seed_workshops()
        created = ensure_admin(
            settings.admin_email, hash_password(settings.admin_password), settings.admin_name
        )
        status = "dibuat" if created else "sudah ada"
        print(f"Admin {status}: {settings.admin_email}")
        total = one("SELECT COUNT(*)::int AS count FROM workshops")
        print(f"Total workshop di database: {total['count']}")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
