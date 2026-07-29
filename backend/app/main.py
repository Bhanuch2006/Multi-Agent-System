from fastapi import FastAPI

from backend.app.api.routes import router as generate_router
from backend.app.core.config import settings


app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(generate_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}

