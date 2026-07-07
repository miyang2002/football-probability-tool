from fastapi import FastAPI


app = FastAPI(title="Football Probability Tool")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "football-probability-tool"}
