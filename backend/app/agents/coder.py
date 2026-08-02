from __future__ import annotations

from dataclasses import dataclass
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.json_utils import parse_json_object
from backend.app.core.prompts import load_prompt
from backend.app.graph.state import AgentState


def _bundle_from_files(files: dict[str, str]) -> str:
    sections: list[str] = []
    for relative_path, content in files.items():
        sections.append(f"## {relative_path}\n\n```text\n{content}\n```")
    return "\n\n".join(sections)


def _fallback_files(state: AgentState) -> dict[str, str]:
    architecture = dict(state.get("architecture", {}))
    project_name = str(state.get("project_name", "FastAPI Project"))
    notes = "\n".join(f"- {note}" for note in state.get("research_notes", []))
    task_hint = str(state.get("task_hint", "")).lower()

    if task_hint == "database":
        return {
            "app/database.py": (
                "try:\n"
                "    from sqlalchemy import create_engine\n"
                "    from sqlalchemy.orm import sessionmaker, declarative_base\n"
                "except Exception:\n"
                "    create_engine = None\n"
                "    def sessionmaker(*args, **kwargs):\n"
                "        class _Session:\n"
                "            def close(self):\n"
                "                return None\n"
                "        return lambda: _Session()\n"
                "    def declarative_base():\n"
                "        class Base:\n"
                "            pass\n"
                "        return Base\n\n"
                "SQLALCHEMY_DATABASE_URL = \"sqlite:///./devcrew.db\"\n"
                "engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={\"check_same_thread\": False}) if create_engine else None\n"
                "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
                "Base = declarative_base()\n"
            ),
            "app/models.py": (
                "try:\n"
                "    from sqlalchemy import Boolean, Column, Integer, String\n"
                "except Exception:\n"
                "    Boolean = Integer = String = object\n"
                "    def Column(*args, **kwargs):\n"
                "        return None\n"
                "from app.database import Base\n\n"
                "class Todo(Base):\n"
                "    __tablename__ = \"todos\"\n"
                "    id = Column(Integer, primary_key=True, index=True)\n"
                "    title = Column(String, nullable=False)\n"
                "    done = Column(Boolean, default=False)\n"
            ),
        }

    if task_hint == "auth":
        return {
            "app/core/security.py": (
                "from datetime import datetime, timedelta, timezone\n"
                "import os\n"
                "from jose import jwt\n"
                "from passlib.context import CryptContext\n\n"
                "SECRET_KEY = os.getenv(\"JWT_SECRET\")\n"
                "if not SECRET_KEY:\n"
                "    raise RuntimeError(\"JWT_SECRET must be set\")\n"
                "ALGORITHM = \"HS256\"\n"
                "ACCESS_TOKEN_EXPIRE_MINUTES = 15\n"
                "pwd_context = CryptContext(schemes=[\"bcrypt\"], deprecated=\"auto\")\n\n"
                "def hash_password(password: str) -> str:\n"
                "    return pwd_context.hash(password)\n\n"
                "def verify_password(plain_password: str, hashed_password: str) -> bool:\n"
                "    return pwd_context.verify(plain_password, hashed_password)\n\n"
                "def create_access_token(subject: str) -> str:\n"
                "    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)\n"
                "    payload = {\"sub\": subject, \"exp\": expires_at}\n"
                "    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)\n"
            ),
            "app/routes/auth.py": (
                "from fastapi import APIRouter, HTTPException\n"
                "from pydantic import BaseModel\n"
                "from app.core.security import create_access_token\n\n"
                "router = APIRouter()\n"
                "USERS = {\"admin\": \"admin123\"}\n"
                "\n"
                "class LoginRequest(BaseModel):\n"
                "    username: str\n"
                "    password: str\n\n"
                "@router.post(\"/login\")\n"
                "def login(payload: LoginRequest):\n"
                "    stored_password = USERS.get(payload.username)\n"
                "    if not stored_password or payload.password != stored_password:\n"
                "        raise HTTPException(status_code=401, detail=\"Invalid credentials\")\n"
                "    return {\"access_token\": create_access_token(payload.username), \"token_type\": \"bearer\"}\n"
            ),
        }

    if task_hint == "crud":
        return {
            "app/database.py": (
                "try:\n"
                "    from sqlalchemy import create_engine\n"
                "    from sqlalchemy.orm import sessionmaker, declarative_base\n"
                "except Exception:\n"
                "    create_engine = None\n"
                "    def sessionmaker(*args, **kwargs):\n"
                "        class _Session:\n"
                "            def close(self):\n"
                "                return None\n"
                "        return lambda: _Session()\n"
                "    def declarative_base():\n"
                "        class Base:\n"
                "            pass\n"
                "        return Base\n\n"
                "SQLALCHEMY_DATABASE_URL = \"sqlite:///./devcrew.db\"\n"
                "engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={\"check_same_thread\": False}) if create_engine else None\n"
                "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
                "Base = declarative_base()\n"
            ),
            "app/models.py": (
                "try:\n"
                "    from sqlalchemy import Boolean, Column, Integer, String\n"
                "except Exception:\n"
                "    Boolean = Integer = String = object\n"
                "    def Column(*args, **kwargs):\n"
                "        return None\n"
                "from app.database import Base\n\n"
                "class Todo(Base):\n"
                "    __tablename__ = \"todos\"\n"
                "    id = Column(Integer, primary_key=True, index=True)\n"
                "    title = Column(String, nullable=False)\n"
                "    done = Column(Boolean, default=False)\n"
            ),
            "app/main.py": (
                "from fastapi import FastAPI\n"
                "from app.routes.auth import router as auth_router\n"
                "from app.routes.todos import router as todos_router\n\n"
                f"app = FastAPI(title=\"{project_name}\")\n\n"
                "app.include_router(auth_router, prefix=\"/auth\", tags=[\"auth\"])\n"
                "app.include_router(todos_router, prefix=\"/todos\", tags=[\"todos\"])\n"
                "\n"
                "@app.get(\"/health\")\n"
                "def health():\n"
                "    return {\"status\": \"ok\"}\n"
            ),
            "app/schemas.py": (
                "from pydantic import BaseModel\n\n"
                "class TodoCreate(BaseModel):\n"
                "    title: str\n"
                "    done: bool = False\n\n"
                "class TodoRead(TodoCreate):\n"
                "    id: int\n"
            ),
            "app/routes/todos.py": (
                "from fastapi import APIRouter, Depends\n"
                "from typing import Any\n"
                "from app.database import SessionLocal\n"
                "from app.schemas import TodoCreate, TodoRead\n\n"
                "router = APIRouter()\n"
                "TODOS: list[TodoRead] = []\n"
                "NEXT_ID = 1\n\n"
                "def get_db():\n"
                "    db = SessionLocal()\n"
                "    try:\n"
                "        yield db\n"
                "    finally:\n"
                "        db.close()\n\n"
                "@router.get(\"/\", response_model=list[TodoRead])\n"
                "def list_todos(db: Any = Depends(get_db)):\n"
                "    return TODOS\n\n"
                "@router.post(\"/\", response_model=TodoRead)\n"
                "def create_todo(todo: TodoCreate, db: Any = Depends(get_db)):\n"
                "    global NEXT_ID\n"
                "    item = TodoRead(id=NEXT_ID, title=todo.title, done=todo.done)\n"
                "    TODOS.append(item)\n"
                "    NEXT_ID += 1\n"
                "    return item\n"
            ),
        }

    if task_hint == "docker":
        return {
            "Dockerfile": (
                "FROM python:3.13-slim\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n"
                "COPY . .\n"
                "CMD [\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]\n"
            ),
            ".dockerignore": "__pycache__\n.venv\n.git\n",
        }

    if task_hint == "ci":
        return {
            ".github/workflows/ci.yml": (
                "name: ci\n"
                "on: [push, pull_request]\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: '3.13'\n"
                "      - run: pip install -r requirements.txt\n"
                "      - run: pytest -q\n"
            ),
        }

    if task_hint == "frontend":
        return {
            "frontend/README.md": "Frontend placeholder generated because the user requested frontend work.",
        }

    files = {
        "requirements.txt": (
            "fastapi\nuvicorn[standard]\nSQLAlchemy>=2.0\npython-jose[cryptography]\n"
            "passlib[bcrypt]\npydantic\npython-dotenv\n"
        ),
        "app/__init__.py": "",
        "app/main.py": (
            "from fastapi import FastAPI\n"
            "from app.routes.auth import router as auth_router\n"
            "from app.routes.todos import router as todos_router\n\n"
            f"app = FastAPI(title=\"{project_name}\")\n\n"
            "app.include_router(auth_router, prefix=\"/auth\", tags=[\"auth\"])\n"
            "app.include_router(todos_router, prefix=\"/todos\", tags=[\"todos\"])\n\n"
            "@app.get(\"/health\")\n"
            "def health():\n"
            "    return {\"status\": \"ok\"}\n"
        ),
        "app/core/__init__.py": "",
        "app/core/config.py": (
            "import os\n\n"
            "APP_NAME = os.getenv(\"APP_NAME\", \"DevCrew API\")\n"
            "JWT_SECRET = os.getenv(\"JWT_SECRET\")\n"
        ),
        "app/core/security.py": (
            "from datetime import datetime, timedelta, timezone\n"
            "import os\n"
            "from jose import jwt\n"
            "from passlib.context import CryptContext\n\n"
            "SECRET_KEY = os.getenv(\"JWT_SECRET\")\n"
            "if not SECRET_KEY:\n"
            "    raise RuntimeError(\"JWT_SECRET must be set\")\n"
            "ALGORITHM = \"HS256\"\n"
            "ACCESS_TOKEN_EXPIRE_MINUTES = 15\n"
            "pwd_context = CryptContext(schemes=[\"bcrypt\"], deprecated=\"auto\")\n\n"
            "def hash_password(password: str) -> str:\n"
            "    return pwd_context.hash(password)\n\n"
            "def verify_password(plain_password: str, hashed_password: str) -> bool:\n"
            "    return pwd_context.verify(plain_password, hashed_password)\n\n"
            "def create_access_token(subject: str) -> str:\n"
            "    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)\n"
            "    payload = {\"sub\": subject, \"exp\": expires_at}\n"
            "    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)\n"
        ),
        "app/database.py": (
            "from sqlalchemy import create_engine\n"
            "from sqlalchemy.orm import sessionmaker, declarative_base\n\n"
            "SQLALCHEMY_DATABASE_URL = \"sqlite:///./devcrew.db\"\n"
            "engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={\"check_same_thread\": False})\n"
            "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n"
            "Base = declarative_base()\n"
        ),
        "app/models.py": (
            "from sqlalchemy import Boolean, Column, Integer, String\n"
            "from app.database import Base\n\n"
            "class Todo(Base):\n"
            "    __tablename__ = \"todos\"\n"
            "    id = Column(Integer, primary_key=True, index=True)\n"
            "    title = Column(String, nullable=False)\n"
            "    done = Column(Boolean, default=False)\n"
        ),
        "app/schemas.py": (
            "from pydantic import BaseModel\n\n"
            "class TodoCreate(BaseModel):\n"
            "    title: str\n"
            "    done: bool = False\n\n"
            "class TodoRead(TodoCreate):\n"
            "    id: int\n"
        ),
        "app/routes/__init__.py": "",
        "app/routes/auth.py": (
            "from fastapi import APIRouter, HTTPException\n"
            "from pydantic import BaseModel\n"
            "from app.core.security import create_access_token, hash_password, verify_password\n\n"
            "router = APIRouter()\n"
            "USERS = {\"admin\": hash_password(\"admin123\")}\n\n"
            "class LoginRequest(BaseModel):\n"
            "    username: str\n"
            "    password: str\n\n"
            "@router.post(\"/login\")\n"
            "def login(payload: LoginRequest):\n"
            "    stored_password = USERS.get(payload.username)\n"
            "    if not stored_password or not verify_password(payload.password, stored_password):\n"
            "        raise HTTPException(status_code=401, detail=\"Invalid credentials\")\n"
            "    return {\"access_token\": create_access_token(payload.username), \"token_type\": \"bearer\"}\n"
        ),
        "app/routes/todos.py": (
                "from fastapi import APIRouter, Depends\n"
                "from typing import Any\n"
            "from app.database import SessionLocal\n"
            "from app.schemas import TodoCreate, TodoRead\n\n"
            "router = APIRouter()\n"
            "TODOS: list[TodoRead] = []\n"
            "NEXT_ID = 1\n\n"
            "def get_db():\n"
            "    db = SessionLocal()\n"
            "    try:\n"
            "        yield db\n"
            "    finally:\n"
            "        db.close()\n\n"
            "@router.get(\"/\", response_model=list[TodoRead])\n"
                "def list_todos(db: Any = Depends(get_db)):\n"
            "    return TODOS\n\n"
            "@router.post(\"/\", response_model=TodoRead)\n"
                "def create_todo(todo: TodoCreate, db: Any = Depends(get_db)):\n"
            "    global NEXT_ID\n"
            "    item = TodoRead(id=NEXT_ID, title=todo.title, done=todo.done)\n"
            "    TODOS.append(item)\n"
            "    NEXT_ID += 1\n"
            "    return item\n"
        ),
        "tests/test_health.py": (
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n\n"
            "client = TestClient(app)\n\n"
            "def test_health():\n"
            "    response = client.get(\"/health\")\n"
            "    assert response.status_code == 200\n"
            "    assert response.json() == {\"status\": \"ok\"}\n"
        ),
        "docs/research.md": notes,
        "docs/architecture.md": json.dumps(architecture, indent=2),
    }
    return files


@dataclass
class CoderAgent:
    def _client(self, model_name: str) -> ChatGroq:
        return ChatGroq(model=model_name, groq_api_key=settings.groq_api_key, temperature=0)

    def _fallback(self, state: AgentState) -> dict[str, object]:
        project_name = str(state.get("project_name", "FastAPI Project"))
        files = _fallback_files(state)
        bundle_markdown = _bundle_from_files(files)
        return {
            "project_files": files,
            "bundle_markdown": bundle_markdown,
            "final_summary": f"Generated {len(files)} files for {project_name}.",
        }

    def run(self, state: AgentState) -> dict[str, object]:
        model_name = str(state.get("model", settings.groq_model))
        if settings.groq_api_key:
            prompt = load_prompt("coder")
            payload_text = json.dumps(
                {
                    "project_name": state.get("project_name"),
                    "user_request": state.get("user_request"),
                    "task_list": state.get("task_list", []),
                    "architecture": state.get("architecture", {}),
                    "research_notes": state.get("research_notes", []),
                    "review": state.get("review", {}),
                    "revision_count": state.get("revision_count", 0),
                    "task_hint": state.get("task_hint"),
                },
                indent=2,
            )
            response = self._client(model_name).invoke([SystemMessage(content=prompt), HumanMessage(content=payload_text)])
            payload = parse_json_object(str(response.content))
        else:
            payload = self._fallback(state)

        files = {str(key): str(value) for key, value in dict(payload.get("project_files", {})).items()}
        return {
            "project_files": files,
            "bundle_markdown": str(payload.get("bundle_markdown", _bundle_from_files(files))),
            "coding_summary": str(payload.get("final_summary", "")),
            "final_summary": str(payload.get("final_summary", "")),
        }
