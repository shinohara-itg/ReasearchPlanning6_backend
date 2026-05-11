from fastapi import APIRouter

from app.schemas.workspace import (
    WorkspaceLoadResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
)
from app.services.workspace_service import load_workspace, save_workspace


router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.post("/save", response_model=WorkspaceSaveResponse)
def save_workspace_api(request: WorkspaceSaveRequest) -> WorkspaceSaveResponse:
    return save_workspace(request)


@router.get("/load", response_model=WorkspaceLoadResponse)
def load_workspace_api() -> WorkspaceLoadResponse:
    return load_workspace()