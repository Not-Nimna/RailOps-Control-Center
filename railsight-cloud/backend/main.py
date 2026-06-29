"""FastAPI application entry point for RailSight."""

from fastapi import FastAPI

app = FastAPI(title="RailSight Cloud API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
