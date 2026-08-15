"""FinFlow API 入口。"""

from fastapi import FastAPI

from backend.app.api import router as api_router
from backend.app.job_manager import JobManager
from backend.app.ws import router as ws_router

APP_NAME = "FinFlow"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.state.manager = JobManager()
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    """存活检查。"""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
