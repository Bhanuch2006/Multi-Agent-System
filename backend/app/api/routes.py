from fastapi import APIRouter, HTTPException

from backend.app.models.response import GenerateJobResponse, GenerateRequest, JobStatusResponse
from backend.app.services.orchestrator import Orchestrator


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

