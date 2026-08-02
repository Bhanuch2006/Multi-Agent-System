from dataclasses import dataclass
from pathlib import Path
import os


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "DevCrew AI")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY") or None
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    research_model: str = os.getenv("RESEARCH_MODEL", "gemini-2.0-flash")
    review_model: str = os.getenv("REVIEW_MODEL", "claude-3-5-sonnet-latest")
    code_model: str = os.getenv("CODE_MODEL", "deepseek-chat")
    docs_model: str = os.getenv("DOCS_MODEL", "llama-3.1-70b-versatile")
    max_revision_cycles: int = int(os.getenv("MAX_REVISION_CYCLES", "2"))
    max_node_retries: int = int(os.getenv("MAX_NODE_RETRIES", "2"))
    node_timeout_seconds: int = int(os.getenv("NODE_TIMEOUT_SECONDS", "120"))
    search_timeout_seconds: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "8"))
    artifacts_dir: Path = Path(os.getenv("ARTIFACTS_DIR", str(_backend_root() / "generated_projects")))
    prompt_dir: Path = Path(__file__).resolve().parents[1] / "prompts"


settings = Settings()
