import os
import fitz
from pathlib import Path
from typing import Optional
from app.models import FileStatus
from app.config import get_settings


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


class FileScanError(Exception):
    def __init__(self, status: FileStatus, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def validate_folder_path(folder_path: str) -> Path:
    path = Path(folder_path).resolve()
    
    if not path.exists():
        raise FileScanError(FileStatus.ERROR, f"Path does not exist: {folder_path}")
    
    if not path.is_dir():
        raise FileScanError(FileStatus.ERROR, f"Path is not a directory: {folder_path}")
    
    if not os.access(path, os.R_OK):
        raise FileScanError(FileStatus.ERROR, f"Directory not readable: {folder_path}")
    
    return path


def is_supported_file(file_path: Path) -> bool:
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def get_file_size(file_path: Path) -> int:
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


def extract_text_from_txt(file_path: Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            raise FileScanError(FileStatus.SKIPPED_UNREADABLE, f"Cannot decode text file: {e}")
    except PermissionError:
        raise FileScanError(FileStatus.SKIPPED_UNREADABLE, "Permission denied")
    except Exception as e:
        raise FileScanError(FileStatus.ERROR, f"Error reading file: {e}")


def extract_text_from_pdf(file_path: Path) -> str:
    try:
        doc = fitz.open(file_path)
        
        if doc.is_encrypted:
            doc.close()
            raise FileScanError(FileStatus.SKIPPED_ENCRYPTED, "PDF is encrypted")
        
        text_parts = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            if text:
                text_parts.append(text)
        
        doc.close()
        return "\n".join(text_parts)
    
    except fitz.FileDataError:
        raise FileScanError(FileStatus.SKIPPED_UNREADABLE, "Invalid or corrupted PDF")
    except PermissionError:
        raise FileScanError(FileStatus.SKIPPED_UNREADABLE, "Permission denied")
    except FileScanError:
        raise
    except Exception as e:
        raise FileScanError(FileStatus.ERROR, f"Error extracting PDF text: {e}")


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    
    if suffix in {".txt", ".md"}:
        return extract_text_from_txt(file_path)
    elif suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    else:
        raise FileScanError(FileStatus.SKIPPED_UNSUPPORTED, f"Unsupported file type: {suffix}")


def scan_folder(folder_path: str) -> list[dict]:
    settings = get_settings()
    max_file_size_bytes = settings.max_file_size_mb * 1024 * 1024
    max_extracted_text_chars = settings.max_extracted_text_chars
    
    root_path = validate_folder_path(folder_path)
    results = []
    
    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        
        if file_path.is_symlink():
            continue
        
        try:
            relative_path = file_path.relative_to(root_path)
        except ValueError:
            results.append({
                "filename": file_path.name,
                "status": FileStatus.ERROR,
                "error_message": "File path escaped scan directory",
                "text": None,
            })
            continue
        
        if not is_supported_file(file_path):
            results.append({
                "filename": str(relative_path),
                "status": FileStatus.SKIPPED_UNSUPPORTED,
                "error_message": f"Unsupported file type: {file_path.suffix}",
                "text": None,
            })
            continue
        
        file_size = get_file_size(file_path)
        if file_size == 0:
            results.append({
                "filename": str(relative_path),
                "status": FileStatus.SKIPPED_EMPTY,
                "error_message": "File is empty",
                "text": None,
            })
            continue
        
        if file_size > max_file_size_bytes:
            results.append({
                "filename": str(relative_path),
                "status": FileStatus.SKIPPED_OVERSIZED,
                "error_message": f"File exceeds {settings.max_file_size_mb}MB limit",
                "text": None,
            })
            continue
        
        try:
            text = extract_text(file_path)
            
            if not text or not text.strip():
                results.append({
                    "filename": str(relative_path),
                    "status": FileStatus.SKIPPED_EMPTY,
                    "error_message": "No extractable text content",
                    "text": None,
                })
                continue
            
            if len(text) > max_extracted_text_chars:
                text = text[:max_extracted_text_chars]
            
            results.append({
                "filename": str(relative_path),
                "status": FileStatus.SUCCESS,
                "error_message": None,
                "text": text,
            })
        
        except FileScanError as e:
            results.append({
                "filename": str(relative_path),
                "status": e.status,
                "error_message": e.message,
                "text": None,
            })
        except Exception as e:
            results.append({
                "filename": str(relative_path),
                "status": FileStatus.ERROR,
                "error_message": f"Unexpected error: {str(e)[:200]}",
                "text": None,
            })
    
    return results