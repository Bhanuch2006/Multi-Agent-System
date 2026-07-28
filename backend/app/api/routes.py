from fastapi import APIRouter, HTTPException

from app.models.response import GenerateRequest, GenerateResponse
from app.services.orchestrator import Orchestrator


router = APIRouter()
orchestrator = Orchestrator()


@router.post("/generate", response_model=GenerateResponse)
def generate_project(request: GenerateRequest) -> GenerateResponse:
    try:
        result = orchestrator.generate(request.prompt)
    except Exception as exc:  # pragma: no cover - surfaced through API response
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return GenerateResponse.model_validate(result)
