from fastapi import FastAPI

from app.routes import router


app = FastAPI(title="Football Probability Tool")
app.include_router(router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-probability-tool"}
