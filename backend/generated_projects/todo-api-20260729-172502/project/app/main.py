from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.todos import router as todos_router

app = FastAPI(title="Todo API")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(todos_router, prefix="/todos", tags=["todos"])

@app.get("/health")
def health():
    return {"status": "ok"}
