from pathlib import Path
import os


def save_project(artifacts_dir: Path, project_name: str, files: dict) -> Path:
    target = Path(artifacts_dir) / project_name
    os.makedirs(target, exist_ok=True)

    for relpath, content in files.items():
        path = target / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return target
