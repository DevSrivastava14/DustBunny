import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    AppInfo,
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    FileAnalysisResult,
    FileStatus,
    AnalyzeContentsRequest,
    FileContent,
)
from app.scanner import scan_folder, extract_text_from_pdf, FileScanError
from app.ollama import classify_text, OllamaError
from app.config import get_settings

app = FastAPI(title="DustBunny API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=AppInfo)
async def root():
    return AppInfo(
        name="DustBunny",
        version="0.1.0",
        description="Privacy-first local AI file organizer"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="healthy")


async def _process_files(file_items: list[dict]) -> tuple[list[FileAnalysisResult], int, int, int]:
    """Process a list of file items (each with filename and text) through Ollama classification."""
    results = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for item in file_items:
        filename = item["filename"]
        text = item["text"]
        status = item["status"]
        
        if status == FileStatus.SUCCESS:
            try:
                suggestion = await classify_text(text)
                results.append(FileAnalysisResult(
                    filename=filename,
                    status=status,
                    suggestion=suggestion,
                ))
                processed_count += 1
            except OllamaError as e:
                results.append(FileAnalysisResult(
                    filename=filename,
                    status=FileStatus.ERROR,
                    error_message=e.user_message,
                ))
                error_count += 1
            except Exception:
                results.append(FileAnalysisResult(
                    filename=filename,
                    status=FileStatus.ERROR,
                    error_message="AI classification failed unexpectedly",
                ))
                error_count += 1
        else:
            results.append(FileAnalysisResult(
                filename=filename,
                status=status,
                error_message=item.get("error_message"),
            ))
            if status == FileStatus.ERROR:
                error_count += 1
            else:
                skipped_count += 1
    
    return results, processed_count, skipped_count, error_count


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_folder(request: AnalyzeRequest):
    try:
        scanned_files = scan_folder(request.folder_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    results, processed_count, skipped_count, error_count = await _process_files(scanned_files)
    
    return AnalyzeResponse(
        folder_path=request.folder_path,
        total_files=len(scanned_files),
        processed_files=processed_count,
        skipped_files=skipped_count,
        error_files=error_count,
        results=results,
    )


async def _process_uploaded_file(filename: str, content: str, content_base64: str | None, max_file_size_bytes: int) -> dict:
    """Process a single uploaded file (txt/md/pdf) and return file item for analysis."""
    lower_name = filename.lower()
    
    # Validate relative path safety
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        return {
            "filename": filename,
            "text": "",
            "status": FileStatus.ERROR,
            "error_message": "Path traversal or absolute paths not allowed",
        }
    
    if lower_name.endswith(('.txt', '.md')):
        if not content.strip():
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_EMPTY,
                "error_message": "File is empty",
            }
        return {
            "filename": filename,
            "text": content,
            "status": FileStatus.SUCCESS,
        }
    
    if lower_name.endswith('.pdf'):
        if content_base64 is None:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_UNSUPPORTED,
                "error_message": "PDF content missing (base64 encoding required)",
            }
        
        # Decode base64 and check size
        try:
            pdf_bytes = base64.b64decode(content_base64)
        except Exception:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_UNREADABLE,
                "error_message": "Invalid base64 encoding for PDF",
            }
        
        if len(pdf_bytes) == 0:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_EMPTY,
                "error_message": "PDF file is empty",
            }
        
        if len(pdf_bytes) > max_file_size_bytes:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_OVERSIZED,
                "error_message": f"File exceeds {get_settings().max_file_size_mb}MB limit",
            }
        
        # Extract text from PDF bytes using existing logic
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            if doc.is_encrypted:
                doc.close()
                return {
                    "filename": filename,
                    "text": "",
                    "status": FileStatus.SKIPPED_ENCRYPTED,
                    "error_message": "PDF is encrypted",
                }
            
            text_parts = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                if text:
                    text_parts.append(text)
            
            doc.close()
            extracted_text = "\n".join(text_parts)
            
            if not extracted_text or not extracted_text.strip():
                return {
                    "filename": filename,
                    "text": "",
                    "status": FileStatus.SKIPPED_EMPTY,
                    "error_message": "No extractable text content in PDF",
                }
            
            # Truncate to max extracted text chars
            max_chars = get_settings().max_extracted_text_chars
            if len(extracted_text) > max_chars:
                extracted_text = extracted_text[:max_chars]
            
            return {
                "filename": filename,
                "text": extracted_text,
                "status": FileStatus.SUCCESS,
            }
        
        except fitz.FileDataError:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.SKIPPED_UNREADABLE,
                "error_message": "Invalid or corrupted PDF",
            }
        except Exception as e:
            return {
                "filename": filename,
                "text": "",
                "status": FileStatus.ERROR,
                "error_message": f"Error extracting PDF text: {str(e)[:200]}",
            }
    
    # Unsupported file type
    return {
        "filename": filename,
        "text": "",
        "status": FileStatus.SKIPPED_UNSUPPORTED,
        "error_message": f"Unsupported file type: only .txt, .md, and .pdf are supported",
    }


@app.post("/analyze-contents", response_model=AnalyzeResponse)
async def analyze_contents(request: AnalyzeContentsRequest):
    """Analyze file contents provided directly (for browser-based folder selection)."""
    settings = get_settings()
    max_file_size_bytes = settings.max_file_size_mb * 1024 * 1024
    
    file_items = []
    for fc in request.files:
        file_item = await _process_uploaded_file(
            fc.filename, fc.content, fc.content_base64, max_file_size_bytes
        )
        file_items.append(file_item)
    
    results, processed_count, skipped_count, error_count = await _process_files(file_items)
    
    return AnalyzeResponse(
        folder_path="browser-selected-folder",
        total_files=len(file_items),
        processed_files=processed_count,
        skipped_files=skipped_count,
        error_files=error_count,
        results=results,
    )