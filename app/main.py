from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes import router


app = FastAPI(title="Football Probability Tool")
app.include_router(router)

STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-probability-tool"}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")
