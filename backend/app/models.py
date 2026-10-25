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


RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def _validate_filename(v: str) -> str:
    """Validate suggested_filename - no path separators, no extensions recommended but allowed."""
    if not v or not v.strip():
        raise ValueError("suggested_filename cannot be empty")
    if ".." in v or v.startswith("/") or v.startswith("\\"):
        raise ValueError("suggested_filename: path traversal or absolute paths not allowed")
    if any(c in v for c in '<>:"|?*'):
        raise ValueError("suggested_filename: invalid characters in path")
    if v.strip() != v:
        raise ValueError("suggested_filename: leading/trailing whitespace not allowed")
    if len(v) > 200:
        raise ValueError("suggested_filename: too long (max 200 characters)")
    # Check reserved names (Windows) - use basename without extension
    name_upper = v.split(".")[0].upper()
    if name_upper in RESERVED_NAMES:
        raise ValueError(f"suggested_filename: '{v}' is a reserved system name")
    # Must contain at least one alphanumeric
    if not any(c.isalnum() for c in v):
        raise ValueError("suggested_filename: must contain at least one alphanumeric character")
    # Only allow alphanumeric, hyphen, underscore, dot
    if not all(c.isalnum() or c in "-_." for c in v):
        raise ValueError("suggested_filename: only alphanumeric, hyphen, underscore, and dot allowed")
    return v


def _validate_folder(v: str) -> str:
    """Validate suggested_folder - allow forward slashes for nested paths."""
    if not v or not v.strip():
        raise ValueError("suggested_folder cannot be empty")
    if ".." in v:
        raise ValueError("suggested_folder: path traversal not allowed")
    if v.startswith("/") or v.startswith("\\"):
        raise ValueError("suggested_folder: absolute paths not allowed")
    if any(c in v for c in '<>:"|?*'):
        raise ValueError("suggested_folder: invalid characters in path")
    if v.strip() != v:
        raise ValueError("suggested_folder: leading/trailing whitespace not allowed")
    if len(v) > 200:
        raise ValueError("suggested_folder: too long (max 200 characters)")
    # Must contain at least one alphanumeric
    if not any(c.isalnum() for c in v):
        raise ValueError("suggested_folder: must contain at least one alphanumeric character")
    # Allow alphanumeric, hyphen, underscore, dot, and forward slash for nested folders
    if not all(c.isalnum() or c in "-_./" for c in v):
        raise ValueError("suggested_folder: only alphanumeric, hyphen, underscore, dot, and forward slash allowed")
    # No empty path segments (e.g., "folder//subfolder" or "/folder" or "folder/")
    if v.startswith("/") or v.endswith("/") or "//" in v:
        raise ValueError("suggested_folder: empty path segments not allowed")
    # Check each path segment for reserved names
    for segment in v.split("/"):
        if segment.upper() in RESERVED_NAMES:
            raise ValueError(f"suggested_folder: '{segment}' is a reserved system name")
    return v


class OllamaSuggestion(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    suggested_filename: str = Field(..., min_length=1, max_length=200)
    suggested_folder: str = Field(..., min_length=1, max_length=200)
    explanation: str = Field(..., min_length=1, max_length=1000)
    uncertainty: float = Field(..., ge=0.0, le=1.0)

    @field_validator("suggested_filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        return _validate_filename(v)

    @field_validator("suggested_folder")
    @classmethod
    def validate_folder(cls, v: str) -> str:
        return _validate_folder(v)


class FileAnalysisResult(BaseModel):
    filename: str
    status: FileStatus
    suggestion: Optional[OllamaSuggestion] = None
    error_message: Optional[str] = None


class AnalyzeRequest(BaseModel):
    folder_path: str = Field(..., min_length=1)


class FileContent(BaseModel):
    filename: str = Field(..., min_length=1)
    content: str = Field(default="", min_length=0)
    content_base64: Optional[str] = Field(default=None, description="Base64-encoded binary content for PDF files")


class AnalyzeContentsRequest(BaseModel):
    files: list[FileContent] = Field(..., min_length=1)


class AnalyzeResponse(BaseModel):
    folder_path: str
    total_files: int
    processed_files: int
    skipped_files: int
    error_files: int
    results: list[FileAnalysisResult]