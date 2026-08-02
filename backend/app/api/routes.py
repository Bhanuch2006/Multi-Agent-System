from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from backend.app.models.response import GenerateJobResponse, GenerateRequest, JobStatusResponse
from backend.app.services.orchestrator import Orchestrator
from backend.app.services.project_store import list_artifacts, zip_artifact
from backend.app.services.job_store import job_store


router = APIRouter()
orchestrator = Orchestrator()


@router.post("/generate", response_model=GenerateJobResponse)
def generate_project(request: GenerateRequest) -> GenerateJobResponse:
    try:
        result = orchestrator.submit(request.prompt)
    except Exception as exc:  # pragma: no cover - surfaced through API response
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return GenerateJobResponse.model_validate(result)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str) -> JobStatusResponse:
    status = orchestrator.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JobStatusResponse.model_validate(status)


@router.get("/download/{job_id}")
def download_project(job_id: str):
    record = job_store.get(job_id)
    if not record or not record.result:
        raise HTTPException(status_code=404, detail="Unknown job_id or result not available")
    artifact_path = record.result.get("artifact_path") if isinstance(record.result, dict) else None
    if not artifact_path:
        raise HTTPException(status_code=404, detail="No artifact available for this job")
    archive = zip_artifact(Path(artifact_path))
    return FileResponse(path=archive, filename=archive.name, media_type="application/zip")


@router.get("/projects")
def list_projects():
    base = Path("backend/generated_projects")
    projects = [p.name for p in list_artifacts(base)]
    return {"projects": projects}

