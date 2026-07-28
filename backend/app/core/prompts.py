from pathlib import Path

from app.core.config import settings


def load_prompt(name: str) -> str:
    prompt_path = Path(settings.prompt_dir) / f"{name}.txt"
    return prompt_path.read_text(encoding="utf-8")
