# DustBunny Development Progress

## Project Overview

**DustBunny** is a privacy-first, local-first AI file organizer. It uses an open-weight model through Ollama (currently `gemma3:1b`) to scan a user-selected folder and suggest file categories, descriptive filenames, destination folders, and explanations. It is **recommendation-only**: it never automatically renames, moves, or deletes files.

**Architecture:**
- **Frontend**: React 19 + Vite, styled with CSS custom properties (light/dark mode)
- **Backend**: FastAPI 0.115, Pydantic 2.9, running on port 8000
- **AI Inference**: Local Ollama server on port 11434
- **Supported file types**: `.txt`, `.md`, `.pdf`
- **CORS**: Configured for `http://localhost:5173`, `http://127.0.0.1:5173`, `http://[::1]:5173`

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
- Ollama must be running locally with `gemma3:1b` model pulled (`ollama pull gemma3:1b`)
- Backend must have filesystem access to the folder path entered (Windows paths like `C:\Users\...` work; WSL paths need `/mnt/c/...`)
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
ollama pull gemma3:1b
ollama serve
```
- Verify: `http://127.0.0.1:11434/api/tags` should list `gemma3:1b`

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