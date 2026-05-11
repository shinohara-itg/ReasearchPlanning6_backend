import json
from pathlib import Path

from app.schemas.workspace import (
    WorkspaceLoadResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORKSPACE_FILE = DATA_DIR / "project.json"


def save_workspace(data: WorkspaceSaveRequest) -> WorkspaceSaveResponse:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = data.model_dump()

    with WORKSPACE_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return WorkspaceSaveResponse(
        message="workspace saved successfully",
        saved_path=str(WORKSPACE_FILE),
    )


def load_workspace() -> WorkspaceLoadResponse:
    if not WORKSPACE_FILE.exists():
        return WorkspaceLoadResponse()

    with WORKSPACE_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    return WorkspaceLoadResponse(**payload)