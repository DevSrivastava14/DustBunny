from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class FileStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"
    SKIPPED_EMPTY = "skipped_empty"
    SKIPPED_UNREADABLE = "skipped_unreadable"
    SKIPPED_ENCRYPTED = "skipped_encrypted"
    SKIPPED_OVERSIZED = "skipped_oversized"
    ERROR = "error"


class AppInfo(BaseModel):
    name: str
    version: str
    description: str


class HealthResponse(BaseModel):
    status: str


class OllamaSuggestion(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    suggested_filename: str = Field(..., min_length=1, max_length=255)
    suggested_folder: str = Field(..., min_length=1, max_length=255)
    explanation: str = Field(..., min_length=1, max_length=1000)
    uncertainty: float = Field(..., ge=0.0, le=1.0)

    @field_validator("suggested_filename", "suggested_folder")
    @classmethod
    def validate_safe_path(cls, v: str) -> str:
        if ".." in v or v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path traversal or absolute paths not allowed")
        if any(c in v for c in '<>:"|?*'):
            raise ValueError("Invalid characters in path")
        return v


class FileAnalysisResult(BaseModel):
    filename: str
    status: FileStatus
    suggestion: Optional[OllamaSuggestion] = None
    error_message: Optional[str] = None


class AnalyzeRequest(BaseModel):
    folder_path: str = Field(..., min_length=1)


class AnalyzeResponse(BaseModel):
    folder_path: str
    total_files: int
    processed_files: int
    skipped_files: int
    error_files: int
    results: list[FileAnalysisResult]