from fastapi import APIRouter, Depends, HTTPException
from app.models import TodoCreate, TodoRead

router = APIRouter()
TODOS: list[TodoRead] = []
NEXT_ID = 1

def require_user() -> str:
    return "admin"

@router.get("/", response_model=list[TodoRead])
def list_todos(user: str = Depends(require_user)):
    return TODOS

@router.post("/", response_model=TodoRead)
def create_todo(todo: TodoCreate, user: str = Depends(require_user)):
    global NEXT_ID
    item = TodoRead(id=NEXT_ID, title=todo.title, done=todo.done)
    TODOS.append(item)
    NEXT_ID += 1
    return item
