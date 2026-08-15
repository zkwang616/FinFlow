"""REST 接口。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path

router = APIRouter()


class JobRequest(BaseModel):
    ticker: str = Field(min_length=1)
    mode: str = Field(default="mock", pattern="^(mock|real)$")


@router.post("/api/jobs")
async def create_job(req: JobRequest, request: Request) -> dict:
    manager = request.app.state.manager
    job_id = manager.submit(req.model_dump())
    return {"job_id": job_id, "status": "queued"}


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str, request: Request):
    job = request.app.state.manager.db.get_job(job_id)
    if job is None:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return job


@router.get("/api/jobs/{job_id}/events")
async def get_events(job_id: str, request: Request):
    return request.app.state.manager.db.list_events(job_id)


@router.get("/api/jobs/{job_id}/report")
async def get_report(job_id: str, request: Request):
    job = request.app.state.manager.db.get_job(job_id)
    if job is None or not job.get("report_path"):
        return JSONResponse({"error": "report not ready"}, status_code=404)
    return FileResponse(job["report_path"], media_type="text/html")


@router.get("/api/jobs/{job_id}/report.pdf")
async def get_report_pdf(job_id: str, request: Request):
    job = request.app.state.manager.db.get_job(job_id)
    if job is None or not job.get("report_path"):
        return JSONResponse({"error": "report not ready"}, status_code=404)
    pdf_path = Path(job["report_path"]).with_suffix(".pdf")
    if not pdf_path.exists():
        return JSONResponse({"error": "pdf not generated"}, status_code=404)
    return FileResponse(pdf_path, media_type="application/pdf")
