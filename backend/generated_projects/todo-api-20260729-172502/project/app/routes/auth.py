from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.security import create_access_token, hash_password, verify_password

router = APIRouter()
USERS = {"admin": hash_password("admin123")}

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(payload: LoginRequest):
    stored_password = USERS.get(payload.username)
    if not stored_password or not verify_password(payload.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token(payload.username), "token_type": "bearer"}
