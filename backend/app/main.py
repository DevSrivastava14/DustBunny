from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    AppInfo,
    HealthResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    FileAnalysisResult,
    FileStatus,
)
from app.scanner import scan_folder
from app.ollama import classify_text, OllamaError

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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_folder(request: AnalyzeRequest):
    try:
        scanned_files = scan_folder(request.folder_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    results = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    for scanned in scanned_files:
        status = scanned["status"]
        
        if status == FileStatus.SUCCESS:
            text = scanned["text"]
            try:
                suggestion = await classify_text(text)
                results.append(FileAnalysisResult(
                    filename=scanned["filename"],
                    status=status,
                    suggestion=suggestion,
                ))
                processed_count += 1
            except OllamaError as e:
                results.append(FileAnalysisResult(
                    filename=scanned["filename"],
                    status=FileStatus.ERROR,
                    error_message=e.user_message,
                ))
                error_count += 1
            except Exception:
                results.append(FileAnalysisResult(
                    filename=scanned["filename"],
                    status=FileStatus.ERROR,
                    error_message="AI classification failed unexpectedly",
                ))
                error_count += 1
        else:
            results.append(FileAnalysisResult(
                filename=scanned["filename"],
                status=status,
                error_message=scanned["error_message"],
            ))
            if status == FileStatus.ERROR:
                error_count += 1
            else:
                skipped_count += 1
    
    return AnalyzeResponse(
        folder_path=request.folder_path,
        total_files=len(scanned_files),
        processed_files=processed_count,
        skipped_files=skipped_count,
        error_files=error_count,
        results=results,
    )