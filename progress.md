# DustBunny Development Progress

## Project Overview

**DustBunny** is a privacy-first, local-first AI file organizer. It uses an open-weight model through Ollama (currently `qwen3.5:2b`) to scan a user-selected folder and suggest file categories, descriptive filenames, destination folders, and explanations. It is **recommendation-only**: it never automatically renames, moves, or deletes files.

**Architecture:**
- **Frontend**: React 19 + Vite, styled with CSS custom properties (light/dark mode)
- **Backend**: FastAPI 0.115, Pydantic 2.9, running on port 8000
- **AI Inference**: Local Ollama server on port 11434
- **Supported file types**: `.txt`, `.md`, `.pdf`
- **CORS**: Configured for `http://localhost:5173`, `http://127.0.0.1:5173`, `http://[::1]:5173`

---
 
### Day 4 Polish & Documentation (2026-10-25)

**Loading Overlay Replacement**
- **Removed full-screen loading overlay** that blocked UI during analysis.
- **Inline loading state** on Analyze button: animated spinner + "Analyzing…" label; button disabled to prevent duplicate submissions.
- Page remains fully visible and usable; no fake progress percentages.
- Removed unused `progress` state and all `setProgress()` calls from handlers.

**Summary Metrics Alignment Fix**
- **Fixed Analysis Results summary grid**: Total, Processed, Skipped, Errors now align consistently.
- Added `min-height: 100px` and `justify-content: center` to `.summary-item` for equal card heights.
- Responsive: stacks 2×2 on <640px.

**Comprehensive README.md**
- Created polished root `README.md` with:
  - Project title, tagline, problem/solution overview
  - Typical workflow (step-by-step commands)
  - Feature table, privacy & security guarantees
  - Technology stack + architecture diagram
  - Repository structure (actual files)
  - Prerequisites, installation, configuration, exact run commands
  - Ollama setup (`qwen3.5:2b`, `think: false` rationale)
  - API endpoints with request/response examples
  - Limitations, troubleshooting table, contributing guide
  - Roadmap (parallel requests, file preview, history, desktop packaging)
- No invented badges, screenshots, deployment links, or unsupported features.

**Verification Results (local, Day 4 polish)**

| Check | Result |
|-------|--------|
| Frontend lint (`npm run lint` / oxlint) | **passed** (0 errors) |
| Frontend production build (`npm run build` / vite) | **passed** (231 kB JS, 12.0 kB CSS gzipped) |
| Backend pytest (`python -m pytest tests/` -v) | **71 passed, 2 skipped** |

**Changed files (Day 4 polish)**

| File | Type | Summary |
|------|------|---------|
| `frontend/src/App.jsx` | Modified | Removed full-screen loading overlay, inline button spinner, removed `progress` state |
| `frontend/src/App.css` | Modified | Removed `.loading-overlay` styles, fixed `.summary-item` min-height/alignment |
| `README.md` | Added | Complete project documentation (see above) |

---

### Day 4 (2026-10-25) — UI Redesign, Performance Timing, Recommendation Reliability

**UI Redesign — Modern dark theme, polished Hacktoberfest showcase**
- **Removed development status**: Backend health card ("Backend: Healthy") removed from user-facing UI. Backend `/health` endpoint remains functional. If backend is unreachable when user starts analysis, a friendly actionable error is shown instead.
- **New color palette & design system**: CSS custom properties for consistent theming (dark default, light via `prefers-color-scheme`). Refined spacing, typography (system font stack), border radius, shadows, transitions.
- **Hero/header**: Gradient title, subtle accent underline, cleaner subtitle.
- **Cards**: Elevated dark surfaces with hover shadows, accent left-border on result cards (green=success, amber=skipped, red=error).
- **Folder picker**: Styled secondary button with folder icon, selected-folder hint with animated pulse indicator.
- **Buttons**: Primary (accent gradient + shadow), secondary (subtle border), disabled states, loading spinner inline on Analyze button.
- **Summary grid**: Color-coded stat cards (total/processed/skipped/errors) with larger typography.
- **Result cards**: Cleaner header with filename + status badge, improved suggestion grid layout.
- **Copy buttons**: SVG icons, hover/tap feedback, success/error transient states.
- **Confidence bar**: Thicker bar (10px), color-coded fill (success/warning/error), label with High/Medium/Low + percentage, tooltip disclaimer.
- **Error states**: Consistent red-tinted cards with icons, actionable messaging.
- **Loading overlay**: Full-screen modal with spinner, stage text, progress counter, detail text — honest progress without fake percentages.
- **Responsive**: Stacks on <640px, touch-friendly tap targets.
- **No new dependencies** — pure CSS/React.

**Performance Timing — Lightweight observability**
- **Ollama call timing** (`backend/app/ollama.py`): Added `time.perf_counter()` measurements around each HTTP request attempt.
- **Logs**: On success — `total_ms`, `attempts`, `category`; on timeout/retry — `attempt`, `duration_ms`; on max retries — `total_ms`.
- **Prompt size logging**: Input chars, prompt chars, response chars, `done` flag.
- **No document contents or secrets logged** — only metadata.
- **Root cause of slow analysis**: Sequential per-file Ollama calls (no parallelization) with 60s timeout + 2 retries. Each file incurs full model load + generation. For N files, worst-case ~N × 60s. Prompt size (up to 8k chars) adds marginal overhead. No redundant calls or prompt bloat found.
- **Optimization applied**: Input truncation to 8k chars (already in place) prevents context overflow. No further safe optimizations without parallelizing (adds complexity, may hit Ollama concurrency limits) or reducing timeout (risks cutting off valid generations). Documented for future work.

**Recommendation Reliability — Stricter validation**
- **Filename/folder validation** (`backend/app/models.py`): New `_validate_filename_chars()` enforces:
  - No path traversal (`..`), absolute paths, leading/trailing whitespace
  - No invalid chars (`<>:"|?*`), only alphanumeric, hyphen, underscore, dot
  - Max 200 chars (down from 255)
  - Windows reserved names blocked (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`)
  - Must contain ≥1 alphanumeric character
- **Pydantic `OllamaSuggestion` validators** run on every AI response — invalid suggestions become per-file errors without blocking other files.
- **Uncertainty honesty**: Confidence label derives from model's own uncertainty (0–1), labeled High/Medium/Low with "(approximate model estimate)" disclaimer.
- **Explanation grounding**: Prompt unchanged — requires evidence from provided text only.

**New Backend Tests**
- `test_ollama.py::TestClassifyText`:
  - `test_timing_logged_on_success` — verifies INFO log with `total_ms`, `attempts`
  - `test_timing_logged_on_timeout` — verifies WARNING log with `duration_ms` on timeout
- `test_ollama.py::TestOllamaSuggestionValidation` (12 tests):
  - Valid names, underscores, dots
  - Path traversal (`../`, `/absolute`) rejected
  - Invalid chars (`<>:"|?*`, colon, `@`) rejected
  - Leading/trailing whitespace rejected
  - Length >200 rejected
  - Reserved names (`CON`, `PRN`, `COM1`, `LPT1`, etc.) rejected with/without extension
  - No-alphanumeric rejected
  - Non-allowed chars (`@`, etc.) rejected
  - Folder same validation as filename

**Verification Results (local, Day 4)**

| Check | Result |
|-------|--------|
| Frontend lint (`npm run lint` / oxlint) | **passed** (0 errors) |
| Frontend production build (`npm run build` / vite) | **passed** (232 kB JS, 12.7 kB CSS gzipped) |
| Backend pytest (`python -m pytest tests/` -v) | **71 passed, 2 skipped** |
| Backend test breakdown | `test_analyze.py`: 23 tests; `test_ollama.py`: 32 tests (16 + 2 timing + 12 validation + think:false + truncation); `test_scanner.py`: 19 tests |

**Changed files (Day 4)**

| File | Type | Summary |
|------|------|---------|
| `frontend/src/App.jsx` | Modified | Removed backend health card, added loading overlay with progress, inline button spinner, SVG icons, refined copy feedback |
| `frontend/src/App.css` | Rewritten | Complete redesign: CSS custom properties design system, dark/light themes, modern card/button/form styles, confidence bar, loading overlay, responsive |
| `backend/app/ollama.py` | Modified | Added `time.perf_counter()` timing around HTTP calls, per-attempt + total duration logging, prompt/response size logging |
| `backend/app/models.py` | Modified | Added `_validate_filename_chars()` with reserved names, length, charset, reserved name checks; updated `OllamaSuggestion` validators |
| `backend/tests/test_ollama.py` | Modified | +2 timing tests, +12 validation tests in new `TestOllamaSuggestionValidation` class |

**Remaining limitations**
- Analysis speed scales linearly with file count (sequential Ollama calls). Parallelization would need Ollama concurrency testing.
- Browser folder picker requires HTTPS/localhost (File System Access API constraint).
- Very large PDFs may hit browser memory limits during base64 encoding.
- Manual path entry still available for backend filesystem scanning (supports all file types).

---

### Day 3 (2026-10-25)

**Model switch: Qwen 3.5 2B with thinking disabled**
- **Installed model**: `qwen3.5:2b` (2B parameters) — no 3.5B variant available locally
- **Configuration changes**:
  - `backend/app/config.py`: `ollama_model = "qwen3.5:2b"`
  - `.env.example`: `OLLAMA_MODEL=qwen3.5:2b`
  - `backend/tests/test_analyze.py`: Updated model-not-found test to reference new tag
- **Thinking mode disabled** (`backend/app/ollama.py:48`): Added `"think": false` to Ollama request payload
  - Reduces latency from ~77s to ~3.6s for simple prompts
  - Returns clean JSON without reasoning traces
  - New test: `test_request_includes_think_false` verifies parameter is sent
- All existing functionality preserved: structured prompt, JSON parsing, Pydantic validation, retries, timeouts, actionable errors, path-safety checks

**Folder selection via File System Access API**
- **Constraint**: Browser cannot provide absolute filesystem path to backend. Native picker requires Tauri/Electron or native helper (not added).
- **Solution**: Browser reads `.txt`/`.md` files via `showDirectoryPicker()` and sends contents to new `/analyze-contents` endpoint. PDFs require manual path entry (backend scans filesystem directly).
- **Backend** (`backend/app/main.py`):
  - New `AnalyzeContentsRequest` / `FileContent` models in `models.py`
  - New `POST /analyze-contents` endpoint accepts `{ files: [{filename, content}] }`
  - Shared `_process_files()` helper avoids duplication with `/analyze`
  - Supports txt/md; skips unsupported/empty files with appropriate status
- **Frontend** (`frontend/src/App.jsx`, `frontend/src/App.css`):
  - "Browse…" button appears when `showDirectoryPicker` is supported
  - Recursively reads txt/md files from picked directory
  - Shows "Selected: <folder> (browser picker — .txt/.md only)" hint
  - Manual path entry still works for PDFs and unsupported browsers
  - Dark-mode styles for new browse button
- **New backend tests** (`backend/tests/test_analyze.py::TestAnalyzeContentsEndpoint`): 7 tests covering success, unsupported files, empty files, Ollama errors, validation

**Verification Results (local, Day 3)**

| Check | Result |
|-------|--------|
| Frontend lint (`npm run lint` / oxlint) | **passed** (0 errors) |
| Frontend production build (`npm run build` / vite) | **passed** (230 kB JS, 10.5 kB CSS gzipped) |
| Backend pytest (`python -m pytest tests/` -v) | **48 passed, 2 skipped** |
| Backend test breakdown | `test_analyze.py`: 18 tests (11 + 7 new); `test_ollama.py`: 16 tests (incl. think:false); `test_scanner.py`: 19 tests |

**Changed files (Day 3)**

| File | Type | Summary |
|------|------|---------|
| `backend/app/config.py` | Modified | Model tag `qwen3.5:2b` |
| `backend/app/ollama.py` | Modified | Added `think: false` to disable thinking mode |
| `backend/app/models.py` | Modified | Added `AnalyzeContentsRequest`, `FileContent` models |
| `backend/app/main.py` | Modified | New `/analyze-contents` endpoint, shared `_process_files()` helper |
| `backend/tests/test_analyze.py` | Modified | Updated model-not-found test; +7 new tests for `/analyze-contents` |
| `backend/tests/test_ollama.py` | Modified | +1 test verifying `think: false` in request |
| `.env.example` | Modified | Updated default model tag |
| `frontend/src/App.jsx` | Modified | Browse button, File System Access API integration, recursive file reading |
| `frontend/src/App.css` | Modified | Browse button styles, path input wrapper, picked folder hint, dark mode |

**Limitations**
- Browser folder picker only supports `.txt` and `.md` files (PDF parsing would require pdf.js dependency)
- Manual path entry still required for PDFs and when File System Access API unavailable
- No new dependencies added; no Tauri/Electron/native helper introduced

---

### Day 3 Follow-up (2026-10-25) — PDF support in folder picker

**PDF support added to browser-based folder selection**
- **Frontend** (`frontend/src/App.jsx`):
  - Added `readFileAsBase64()` helper using `FileReader.readAsDataURL()`
  - Extended `processDirectory()` to handle `.pdf` files: reads as base64, includes `content_base64` in request
  - File size check (10MB limit) before reading PDF to avoid memory issues
  - Updated UI hints: "supports .txt, .md, and .pdf files" and "browser picker — .txt, .md, .pdf"
- **Backend** (`backend/app/main.py`, `backend/app/models.py`):
  - `FileContent` model: added optional `content_base64` field for PDF binary content
  - New `_process_uploaded_file()` helper: validates path safety, decodes base64, enforces size limits, extracts PDF text using existing `fitz` logic (reused from `scanner.py`)
  - Supports encrypted PDF detection, corrupted PDF handling, oversized rejection, empty content skip
  - Path traversal protection: rejects `..`, absolute paths, invalid chars in filenames
- **No new dependencies** — uses existing `pymupdf` (fitz) and stdlib `base64`

**New backend tests** (`backend/tests/test_analyze.py::TestAnalyzeContentsEndpoint`): +6 tests
- `test_analyze_contents_pdf_success` — valid PDF with text content processed
- `test_analyze_contents_pdf_corrupted` — invalid PDF returns `skipped_unreadable`
- `test_analyze_contents_pdf_encrypted` — password-protected PDF returns `skipped_encrypted`
- `test_analyze_contents_pdf_oversized` — >10MB PDF returns `skipped_oversized`
- `test_analyze_contents_pdf_empty` — zero-byte PDF returns `skipped_empty`
- `test_analyze_contents_mixed_types` — single request with txt, md, pdf all processed
- `test_analyze_contents_path_traversal_rejected` — `..` and absolute paths blocked

**Verification Results (local, Day 3 follow-up)**

| Check | Result |
|-------|--------|
| Frontend lint (`npm run lint` / oxlint) | **passed** (0 errors) |
| Frontend production build (`npm run build` / vite) | **passed** (230 kB JS, 10.5 kB CSS gzipped) |
| Backend pytest (`python -m pytest tests/` -v) | **55 passed, 2 skipped** |
| Backend test breakdown | `test_analyze.py`: 25 tests (11 original + 7 contents + 6 PDF); `test_ollama.py`: 16 tests; `test_scanner.py`: 19 tests |

**Changed files (Day 3 follow-up)**

| File | Type | Summary |
|------|------|---------|
| `backend/app/models.py` | Modified | Added `content_base64` field to `FileContent` model |
| `backend/app/main.py` | Modified | Added `_process_uploaded_file()` with PDF extraction, size limits, path safety |
| `backend/tests/test_analyze.py` | Modified | +6 PDF-focused tests for upload, extraction, validation |
| `frontend/src/App.jsx` | Modified | Added PDF base64 reading, size check, updated UI hints |
| `frontend/src/App.css` | Unchanged | Existing styles cover new functionality |

**Remaining limitations**
- Browser folder picker requires HTTPS or localhost (File System Access API constraint)
- Very large PDFs may hit browser memory limits during base64 encoding
- Manual path entry still available for backend filesystem scanning (supports all file types)

---

### Day 2 (2026-10-24)

**Backend safety & error-message hardening (no behavior change)**
- **Ollama error wrapper** (`backend/app/ollama.py`): `OllamaError` now carries `user_message` separate from internal `message`; all raise sites supply actionable user-facing text without exposing stack traces or internal details
- **Actionable user messages** for every Ollama failure mode:
  - Model not found → `"AI model 'gemma3:1b' not found. Please run: ollama pull gemma3:1b"`
  - Connection refused → `"Cannot connect to the local AI service. Please ensure Ollama is running (run 'ollama serve' in a terminal)."`
  - Timeout → `"AI request timed out after 60 seconds. The model may be loading or overloaded. Please try again."`
  - Invalid JSON → `"AI service returned an invalid response format. Please try again."`
  - Invalid suggestion schema → `"AI service returned an incomplete suggestion. Please try again."`
  - Unexpected errors / max retries → generic actionable fallback
- **Frontend** (`backend/app/main.py`): surfaces `e.user_message` instead of internal `e.message`
- **Path-escape safeguard** in `scanner.py`: `relative_to()` wrapped in `try/except ValueError`; escaped paths recorded as `FileStatus.ERROR` with message "File path escaped scan directory"
- **New backend tests** (all passing):
  - `test_ollama.py`: invalid chars in filename (`<>`), Windows backslash traversal (`..\`), colon in folder, `user_message` field behavior
  - `test_analyze.py`: connection error message, timeout message, model-not-found message
  - `test_scanner.py`: symlink outside root (skipped on Windows), mocked `rglob` escape detection

**Frontend results-review controls**
- **Copy buttons** for "Proposed Filename" and "Destination Folder" using `navigator.clipboard.writeText()`
- **Transient feedback**: success (✓ green, 2s), failure (✕ red, 3s), auto-clears
- **Visual distinction**: proposed values styled in monospace with subtle background/border vs. original filename in header
- **No new dependencies**; graceful clipboard failure handling

**Confidence display & prompt clarification**
- **Pipeline verified**: Ollama returns `uncertainty` (0.0–1.0) → Pydantic validates `ge=0.0, le=1.0` → frontend computes `confidence = (1 - uncertainty) * 100`
- **Prompt improved** (`ollama.py`): explicit guidance for evidence-based uncertainty with concrete examples
  - Shopping list → uncertainty ~0.1–0.2
  - Ambiguous note → ~0.6–0.8
  - Contradictory/sparse → ~0.8–1.0
  - Factors: clarity, ambiguity, evidence strength
- **Fixed stray `)`** in confidence label (`App.jsx:284`) → "Low confidence 5%" (was "Low confidence 5%)")
- **Approximate-estimate disclaimer** added:
  - Label: "(approximate model estimate)"
  - Tooltip on progress bar: "Approximate model self-assessment, not a calibrated probability"
- **New test**: `test_uncertainty_to_confidence_calculation` confirms 0.90→10% and 0.10→90%

**Verification Results (local, Day 2)**

| Check | Result |
|-------|--------|
| Frontend lint (`npm run lint` / oxlint) | **passed** (0 errors) |
| Frontend production build (`npm run build` / vite) | **passed** (228 kB JS, 9.4 kB CSS gzipped) |
| Backend pytest (`python -m pytest tests/` -v) | **41 passed, 2 skipped** |
| Backend test breakdown | `test_analyze.py`: 11 tests; `test_ollama.py`: 13 tests (incl. new); `test_scanner.py`: 19 tests (incl. new) |
| Skipped tests | `test_skip_symlink` (Windows), `test_symlink_outside_root_handled` (Windows) — symlinks not supported on this platform |

**Changed files (Day 2 only)**

| File | Type | Summary |
|------|------|---------|
| `backend/app/ollama.py` | Modified | Error wrapper `user_message`; all error messages user-facing; prompt with uncertainty guidance |
| `backend/app/main.py` | Modified | Use `e.user_message` for frontend error display |
| `backend/app/scanner.py` | Modified | `relative_to` ValueError catch for path-escape safety |
| `backend/app/models.py` | Unchanged | Path-safety validators already present |
| `backend/tests/test_ollama.py` | Modified | +4 new tests (invalid chars, backslash traversal, colon, uncertainty↔confidence) |
| `backend/tests/test_analyze.py` | Modified | +3 new tests (actionable Ollama error messages) |
| `backend/tests/test_scanner.py` | Modified | +2 new tests (path-escape detection) |
| `frontend/src/App.jsx` | Modified | Copy-to-clipboard handler, feedback state, copy buttons, confidence label fix, disclaimer label |
| `frontend/src/App.css` | Modified | Copy button styles, proposed filename/folder styling, uncertainty bar + fill, disclaimer note, dark mode |

**No schema changes, no new dependencies, no automatic file operations, no folder picker.**

---

## Daily Progress

### Day 1 (2026-10-23)

**Project foundation and repository setup**
- Created repository with `backend/` and `frontend/` directories
- Added `.gitignore` and `.env.example` at root
- Frontend initialized with Vite + React 19, Oxlint for linting
- Backend initialized with Python 3.13 virtual environment

**FastAPI application with health endpoints and CORS configuration**
- `GET /` returns application info (name, version, description)
- `GET /health` returns `{"status": "healthy"}`
- CORS middleware allows frontend dev server origins
- Settings loaded via `pydantic-settings` from `.env` (port 8000, Ollama host/model, file size limits)

**Safe file scanning for supported TXT, Markdown, and PDF files**
- `scan_folder()` validates path exists and is a directory
- Recursively walks subdirectories
- Extracts text from `.txt`, `.md` (UTF-8), `.pdf` (via PyMuPDF)
- Skips unsupported extensions, empty files, unreadable files, encrypted PDFs, files > 10 MB
- Symlinks skipped (test skipped on Windows)

**Request/response validation and path-safety checks**
- `AnalyzeRequest`: `folder_path` (required, min_length=1)
- `AnalyzeResponse`: `folder_path`, `total_files`, `processed_files`, `skipped_files`, `error_files`, `results[]`
- `FileAnalysisResult`: `filename`, `status` (enum), optional `suggestion`, optional `error_message`
- `OllamaSuggestion`: `category`, `suggested_filename`, `suggested_folder`, `explanation`, `uncertainty` (0.0–1.0)
- Path-safety validators reject `..`, absolute paths, and invalid chars (`<>:"|?*`)

**Ollama integration and structured AI organization suggestions**
- `classify_text()` calls `POST /api/generate` on Ollama with structured prompt
- Retries on timeout (2 retries, 60s timeout each)
- Parses JSON response, validates against `OllamaSuggestion` schema
- Handles model not found, connection errors, invalid JSON, schema violations

**React frontend integration**
- Folder-path input with placeholder and hint text ("accessible to the backend running on your computer")
- Analyze button with loading state, disabled during request
- Error handling: network errors, HTTP errors, invalid responses
- Summary cards: Total, Processed (green), Skipped (orange), Errors (red)
- Per-file result cards:
  - Filename + status badge (Processed/Skipped/Error)
  - AI suggestion fields labeled as suggestions (category, proposed filename, destination folder, explanation, uncertainty %)
  - "All fields above are AI-generated suggestions. DustBunny never moves, renames, or deletes files." disclaimer
  - Error message display for skipped/failed files
- Backend health indicator preserved in status card
- Dark mode support via CSS custom properties
- Responsive layout (< 600px stacks grid columns)
- API base URL from `import.meta.env.VITE_API_URL` (default `http://localhost:8000`, overridden to `http://127.0.0.1:8000` in `.env`)

**Manual end-to-end testing with a sample folder**
- Tested with folder containing `.txt`, `.md`, `.pdf`, and `.jpg` files
- Backend returned correct counts: processed=3, skipped_unsupported=1
- Each processed file showed category, suggested filename, folder, explanation, uncertainty
- Unsupported `.jpg` showed "Skipped (unsupported type)" with no suggestion
- Invalid path returned 400 with "does not exist" message
- Network error handling verified by stopping backend

**Automated test results (previously reported)**
- Frontend lint (`npm run lint` / oxlint): **passed**
- Frontend production build (`npm run build` / vite): **passed** (226 kB JS, 6.8 kB CSS gzipped)
- Backend tests (`pytest tests/`): **31 passed, 1 skipped** (symlink test skipped on Windows)
  - `test_analyze.py`: 8 tests covering nonexistent folder, file instead of folder, empty folder, TXT files, unsupported files, Ollama error, PDF file, response structure
  - `test_ollama.py`: 10 tests covering success, model not found, connection error, timeout, invalid JSON, invalid suggestion format, path traversal, absolute path, retry on timeout
  - `test_scanner.py`: 14 tests covering validation, scanning, text extraction

**Remaining limitations**
- Ollama must be running locally with `qwen3.5:2b` model pulled (`ollama pull qwen3.5:2b`)
- Backend must have filesystem access to the folder path entered (Windows paths like `C:\Users\...` work; WSL paths need `/mnt/c/...`)
- Browser folder picker only supports `.txt` and `.md` files; PDFs require manual path entry
- No database, authentication, cloud AI, or automatic file operations
- Frontend dev server runs on port 5173; backend on port 8000

**Requirements-file relocation and progress documentation (this work)**
- Moved `backend/requirements.txt` → `requirements.txt` at repository root
- Removed old `backend/requirements.txt`
- Created this `progress.md` at repository root
- Verified no references to old path in project documentation or scripts

---

## Project Structure

```
AI Bunny/
├── .gitignore
├── .env.example
├── requirements.txt          # ← moved here from backend/
├── progress.md               # ← this file
├── backend/
│   ├── app/
│   │   ├── __pycache__/
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── ollama.py
│   │   └── scanner.py
│   ├── tests/
│   │   ├── __pycache__/
│   │   ├── conftest.py
│   │   ├── test_analyze.py
│   │   ├── test_ollama.py
│   │   └── test_scanner.py
│   ├── venv/
│   └── .pytest_cache/
├── frontend/
│   ├── .env                  # VITE_API_URL=http://127.0.0.1:8000
│   ├── .gitignore
│   ├── .oxlintrc.json
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── README.md
│   ├── vite.config.js
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── assets/
│   ├── node_modules/
│   └── dist/
```

---

## How to Run Locally

### Prerequisites
- Python 3.13+ with `venv`
- Node.js 20+ with npm
- Ollama installed and running

### 1. Install Python dependencies (inside backend virtual environment)
```bash
cd backend
.\venv\Scripts\activate
python -m pip install -r ..\requirements.txt
```

### 2. Start the FastAPI backend (port 8000)
```bash
# From backend/ with venv activated
uvicorn app.main:app --reload --port 8000
```
- Health check: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

### 3. Pull and run the configured Ollama model (port 11434)
```bash
ollama pull qwen3.5:2b
ollama serve
```
- Verify: `http://127.0.0.1:11434/api/tags` should list `qwen3.5:2b`

### 4. Start the React frontend (port 5173)
```bash
cd frontend
npm run dev
```
- Opens `http://localhost:5173` (or `http://127.0.0.1:5173`)
- Uses `VITE_API_URL=http://127.0.0.1:8000` from `frontend/.env`

---

## Verification Status

| Item | Status | Notes |
|------|--------|-------|
| Backend health endpoints (`/`, `/health`) | Verified by developer | Manual curl/browser test |
| POST `/analyze` endpoint | Verified by developer | Manual test with sample folder |
| File scanning (txt, md, pdf) | Verified by developer | Manual test; automated tests exist |
| Skip/unsupported/empty/oversized handling | Verified by developer | Manual test; automated tests exist |
| Ollama integration | Verified by developer | Requires Ollama running; automated tests mock it |
| Path-safety validators | Verified by developer | Automated tests cover traversal/absolute paths |
| Frontend analysis UI | Verified by developer | Manual test: input, loading, results, errors |
| Frontend lint (oxlint) | Previously reported | `npm run lint` passed |
| Frontend build (vite) | Previously reported | `npm run build` passed |
| Backend pytest suite | Previously reported | 31 passed, 1 skipped |
| Requirements file at root | Verified by developer | File exists, old file removed |
| Progress.md created | Verified by developer | This file |

**Not yet verified / known limitations:**
- End-to-end automated browser test (no Playwright/Cypress configured)
- Windows symlink handling (test skipped)
- WSL path compatibility (not tested)
- Production deployment (no Docker, no reverse proxy config)

---

## Next-Session Handoff

### Starting the next development day:
1. **Read `progress.md`** and inspect current Git status (`git status`, `git diff`)
2. **Review latest completed work** and unresolved limitations above
3. **Agree on next day's goals** before editing code
4. **Update `progress.md` at end of day** with:
   - Actual changes made (files, functions, behavior)
   - Tests run and results (link to CI or local output)
   - Issues encountered and workarounds
   - Next steps / blockers for following session

### Suggested next goals (not yet agreed):
- Add file preview / text excerpt in result cards
- Implement "copy suggestion" buttons
- Add drag-and-drop folder selection (File System Access API)
- Persist analysis history locally (IndexedDB)
- Package as desktop app (Tauri / Electron)