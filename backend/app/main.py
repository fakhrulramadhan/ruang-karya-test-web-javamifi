"""Entry point FastAPI Ruang Karya."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import close_pool, ensure_admin, initialize_database, open_pool, seed_workshops
from .routers.api import router as api_router
from .routers.auth import router as auth_router
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    initialize_database()
    seed_workshops()
    ensure_admin(settings.admin_email, hash_password(settings.admin_password), settings.admin_name)
    logging.getLogger("ruangkarya").info("Ruang Karya API Python siap di http://localhost:%s", settings.port)
    yield
    close_pool()


app = FastAPI(
    title="Ruang Karya API",
    version="2.0.0",
    description="Backend FastAPI untuk platform workshop Ruang Karya.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, error: Exception):
    logging.getLogger("ruangkarya").exception("Unhandled API error", exc_info=error)
    message = "Terjadi kesalahan pada server." if settings.is_production else str(error)
    return JSONResponse(status_code=500, content={"success": False, "message": message})


# Development convenience: backend juga dapat melayani build frontend.
if settings.dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=settings.dist_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend_fallback(path: str):
        requested = settings.dist_dir / path
        if requested.is_file():
            return FileResponse(requested)
        return FileResponse(settings.dist_dir / "index.html")
