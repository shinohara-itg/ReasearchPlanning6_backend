from typing import Any

from pydantic import BaseModel, Field


class WorkspaceSaveRequest(BaseModel):
    extracted_texts: list[str] = Field(default_factory=list)
    manual_text: str = ""
    orien_outline_text: str = ""
    problem_reframe: dict[str, Any] | None = None
    kickoff: dict[str, Any] | None = None
    subq_list: list[dict[str, Any]] = Field(default_factory=list)
    analysis_blocks: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceLoadResponse(BaseModel):
    extracted_texts: list[str] = Field(default_factory=list)
    manual_text: str = ""
    orien_outline_text: str = ""
    problem_reframe: dict[str, Any] | None = None
    kickoff: dict[str, Any] | None = None
    subq_list: list[dict[str, Any]] = Field(default_factory=list)
    analysis_blocks: list[dict[str, Any]] = Field(default_factory=list)


class WorkspaceSaveResponse(BaseModel):
    message: str
    saved_path: str