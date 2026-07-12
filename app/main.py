import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .routers import cards, collection, market, users
from .seed import seed_database

# Render/Linux slim a menudo no mapea .css/.js y el browser los bloquea como text/plain
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("image/svg+xml", ".svg")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "TCG Trade"}


def _static_file(name: str, media_type: str) -> FileResponse:
    path = STATIC_DIR / name
    return FileResponse(path, media_type=media_type)


@app.get("/")
def index():
    return _static_file("index.html", "text/html; charset=utf-8")


@app.get("/static/styles.css")
def styles_css():
    return _static_file("styles.css", "text/css; charset=utf-8")


@app.get("/static/app.js")
def app_js():
    return _static_file("app.js", "application/javascript; charset=utf-8")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
