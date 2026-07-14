import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .database import Base, SessionLocal, engine
from .routers import cards, collection, market, tournaments, users
from .seed import seed_database

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title="TCG Trade", version="1.0.0", lifespan=lifespan)

app.include_router(users.router)
app.include_router(cards.router)
app.include_router(collection.router)
app.include_router(market.router)
app.include_router(tournaments.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "TCG Trade",
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
        "files": sorted(p.name for p in STATIC_DIR.glob("*")) if STATIC_DIR.exists() else [],
    }


def serve_static(filename: str, media_type: str) -> FileResponse:
    path = STATIC_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"No encontrado: {filename} en {STATIC_DIR}")
    return FileResponse(path, media_type=media_type)


@app.get("/")
def index():
    return serve_static("index.html", "text/html; charset=utf-8")


@app.head("/")
def index_head():
    path = STATIC_DIR / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(path, media_type="text/html; charset=utf-8")


@app.get("/static/styles.css")
def styles_css():
    return serve_static("styles.css", "text/css; charset=utf-8")


@app.get("/static/app.js")
def app_js():
    return serve_static("app.js", "application/javascript; charset=utf-8")
