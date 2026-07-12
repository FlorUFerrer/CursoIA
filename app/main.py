from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .routers import cards, collection, market, users
from .seed import seed_database

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


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
