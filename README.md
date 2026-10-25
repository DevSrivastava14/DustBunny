# DustBunny

**A privacy-first, local-only AI file organizer that suggests how to categorize and rename your files — without ever moving, renaming, or deleting them.**

---

## The Problem

Folders accumulate: `Document1.pdf`, `notes.txt`, `scan_20240115.pdf`, `meeting.md`. Finding anything later is a chore. Cloud AI tools can help, but they upload your files to external servers.

## The Solution

DustBunny runs entirely on your machine. Point it at a folder (or pick one in the browser), and it:

1. **Scans** `.txt`, `.md`, and `.pdf` files locally
2. **Extracts text** (PDF via PyMuPDF, text/markdown directly)
3. **Sends only text** to a local Ollama model (`qwen3.5:2b`)
4. **Returns structured suggestions** per file:
   - Category (e.g., "Financial", "Code", "Personal")
   - Proposed filename (descriptive, no extension)
   - Suggested destination folder
   - One-sentence explanation grounded in the content
   - Confidence estimate (from the model's own uncertainty)
5. **Displays results** with copy buttons — you decide what to do

**No files are ever modified, moved, or deleted.** DustBunny is recommendation-only.

---

## Features

| Feature | Status |
|---------|--------|
| Local-first: all inference on your machine via Ollama | ✅ |
| File System Access API folder picker (browser) | ✅ |
| Manual folder path entry (backend scans filesystem) | ✅ |
| `.txt`, `.md`, `.pdf` support | ✅ |
| PDF text extraction (PyMuPDF) | ✅ |
| AI-generated category, filename, folder, explanation | ✅ |
| Model self-reported confidence (0–100%) | ✅ |
| Copy-to-clipboard for filename & folder | ✅ |
| Dark/light theme (system preference) | ✅ |
| Responsive layout | ✅ |
| Path traversal & reserved-name validation | ✅ |
| Recommendation-only: no auto-rename/move/delete | ✅ |

---

## How It Works (Typical Workflow)

```
1. Start Ollama:     ollama serve
2. Pull model:       ollama pull qwen3.5:2b
3. Start backend:    cd backend && uvicorn app.main:app --port 8000
4. Start frontend:   cd frontend && npm run dev
5. Open http://localhost:5173
6. Click "Browse…" or paste a folder path
7. Review suggestions → copy what you need
```

### Folder Picker vs. Manual Path

| Method | How it works | Supported types |
|--------|--------------|-----------------|
| **Browser "Browse…" button** | Uses File System Access API; browser reads files, sends text/base64 to `/analyze-contents` | `.txt`, `.md`, `.pdf` |
| **Manual path entry** | Backend scans the filesystem directly via `/analyze` | `.txt`, `.md`, `.pdf` |

Both paths produce identical suggestion structures. The manual path is required for PDFs in environments where the File System Access API is unavailable (non-HTTPS/non-localhost).

---

## Privacy & Security

- **Document contents never leave your machine.** Text is sent only to the local Ollama HTTP endpoint (`http://localhost:11434`).
- **No telemetry, no analytics, no cloud calls.**
- **No file operations.** DustBunny only *suggests* — it never writes to your filesystem.
- **Path safety:** Both frontend and backend reject `..`, absolute paths, reserved Windows names (`CON`, `PRN`, `COM1`…), and invalid characters in AI-suggested filenames/folders.
- **File size limit:** 10 MB per file (configurable).
- **Extracted text limit:** 50,000 chars per file sent to the model; model input truncated to 8,000 chars to prevent context overflow.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + Vite, CSS custom properties (dark/light) |
| Backend | FastAPI 0.115, Pydantic 2.9, Uvicorn |
| AI Inference | Ollama (local) — model `qwen3.5:2b` |
| PDF Extraction | PyMuPDF (`fitz`) |
| HTTP Client | `httpx` (async) |
| Testing | `pytest`, `pytest-asyncio` |
| Linting | `oxlint` |

### Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  React Frontend  │────▶│  FastAPI Backend │────▶│  Ollama (local)  │
│  (port 5173)     │     │  (port 8000)     │     │  (port 11434)    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        │ 1. User picks folder   │                        │
        │    or enters path      │                        │
        │                        │ 2. Scan/extract text   │
        │                        │    (txt/md/pdf)        │
        │                        │                        │
        │ 5. Display suggestions │ 4. Return JSON         │
        │    (category, name,    │    (category, name,    │
        │     folder, explain,   │     folder, explain,   │
        │     confidence)        │     confidence)        │
        │                        │                        │
        │                        │ 3. POST /api/generate  │
        │                        │    (prompt + text)     │
```

---

## Repository Structure

```
AI Bunny/
├── .gitignore
├── .env.example          # Example environment variables
├── requirements.txt      # Python dependencies (root)
├── progress.md           # Development diary
├── README.md             # This file
├── backend/
│   ├── app/
│   │   ├── config.py         # Settings (Pydantic Settings)
│   │   ├── main.py           # FastAPI app, endpoints
│   │   ├── models.py         # Pydantic request/response models
│   │   ├── ollama.py         # Ollama client, prompt, timing
│   │   └── scanner.py        # Filesystem scan, text extraction
│   ├── tests/
│   │   ├── test_analyze.py   # API endpoint tests
│   │   ├── test_ollama.py    # Ollama client & validation tests
│   │   └── test_scanner.py   # Scanner tests
│   ├── venv/                 # Python virtual environment
│   └── .pytest_cache/
└── frontend/
    ├── .env                  # VITE_API_URL
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── public/
    │   ├── favicon.svg
    │   └── icons.svg
    └── src/
        ├── main.jsx
        ├── App.jsx           # Main React component
        ├── App.css           # All styles (CSS custom properties)
        └── index.css
```

---

## Getting Started

### Prerequisites

- **Python 3.13+** with `venv`
- **Node.js 20+** with `npm`
- **Ollama** installed and in PATH

### 1. Install Python Dependencies

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r ..\requirements.txt
```

### 2. Start the FastAPI Backend (port 8000)

```bash
# From backend/ with venv activated
uvicorn app.main:app --reload --port 8000
```

- Health check: `http://127.0.0.1:8000/health`
- API docs (Swagger): `http://127.0.0.1:8000/docs`

### 3. Pull and Run the Ollama Model (port 11434)

```bash
ollama pull qwen3.5:2b
ollama serve
```

- Verify: `http://127.0.0.1:11434/api/tags` should list `qwen3.5:2b`
- **`think: false`** is sent in every request to disable reasoning traces and reduce latency (~77s → ~3.6s for simple prompts).

### 4. Start the React Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

- Opens `http://localhost:5173` (or `http://127.0.0.1:5173`)
- Uses `VITE_API_URL=http://127.0.0.1:8000` from `frontend/.env`

---

## Configuration

### Backend (`backend/app/config.py` via `.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen3.5:2b` | Model tag to use |
| `MAX_FILE_SIZE_MB` | `10` | Per-file size limit |
| `MAX_EXTRACTED_TEXT_CHARS` | `50000` | Max chars extracted per file |
| `MAX_ANALYSIS_TEXT_CHARS` | `8000` | Max chars sent to model (truncation) |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Per-request timeout |
| `OLLAMA_MAX_RETRIES` | `2` | Retries on timeout |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend base URL |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | App info (name, version, description) |
| `GET` | `/health` | Health check (`{"status": "healthy"}`) |
| `POST` | `/analyze` | Scan folder on backend filesystem (`{folder_path}`) |
| `POST` | `/analyze-contents` | Analyze pre-read files (`{files: [{filename, content?, content_base64?}]}`) |

### Request/Response Examples

**POST `/analyze`**
```json
// Request
{ "folder_path": "C:/Users/me/Documents" }

// Response
{
  "folder_path": "C:/Users/me/Documents",
  "total_files": 3,
  "processed_files": 2,
  "skipped_files": 1,
  "error_files": 0,
  "results": [
    {
      "filename": "invoice.pdf",
      "status": "success",
      "suggestion": {
        "category": "Financial",
        "suggested_filename": "invoice-2024-001",
        "suggested_folder": "finance",
        "explanation": "Contains invoice with amount, date, and vendor details.",
        "uncertainty": 0.1
      }
    }
  ]
}
```

**POST `/analyze-contents`**
```json
// Request
{
  "files": [
    { "filename": "notes.txt", "content": "Buy milk, eggs, bread" },
    { "filename": "doc.pdf", "content_base64": "JVBERi0xLjQ..." }
  ]
}
```

---

## Limitations

- **Sequential analysis**: Files are processed one-by-one. N files ≈ N × model latency. No parallelization (would require Ollama concurrency testing).
- **Browser picker**: Requires HTTPS or `localhost` (File System Access API constraint).
- **PDF in browser**: Base64-encoded in memory; very large PDFs may hit browser limits.
- **Model input cap**: 8,000 chars per request (configurable). Longer docs are truncated.
- **No database/history**: Results are ephemeral.
- **No authentication/cloud**: Intended for local, single-user use.

---

## Testing

### Backend

```bash
# From repo root
python -m pytest backend/tests/ -v
# 71 passed, 2 skipped (Windows symlink tests)
```

### Frontend

```bash
cd frontend
npm run lint   # oxlint — 0 errors
npm run build  # Vite production build
```

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| "Cannot reach backend" | Backend not running / wrong port | Run `uvicorn app.main:app --port 8000` from `backend/` |
| "AI model not found" | Model not pulled | `ollama pull qwen3.5:2b` |
| "Incomplete suggestion" | Model response truncated / validation failed | Check logs; input may exceed 8k chars; model may need more tokens |
| "PDF skipped (unreadable)" | Corrupted or image-only PDF | Try manual path entry; ensure PDF has extractable text |
| "Backend unavailable" on analyze | Backend crashed or CORS | Check backend logs; ensure CORS allows `localhost:5173` |
| Slow analysis (1–2 min) | Many files × sequential calls | Normal for local 2B model; consider fewer files or smaller docs |

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `npm run lint`, `npm run build`, and `python -m pytest backend/tests/`
5. Submit a PR

**Coding standards:**
- Minimal, focused changes
- No new dependencies without discussion
- Preserve recommendation-only behavior
- Keep dark/light theme support

---

## License

No license file is currently present in this repository. All rights reserved by the authors. A license may be added in a future release.

---

## Roadmap

- Parallel Ollama requests (with concurrency control)
- File preview / text excerpt in result cards
- Drag-and-drop folder selection (File System Access API)
- Persist analysis history locally (IndexedDB)
- Desktop packaging (Tauri / Electron)
- Batch rename/move with confirmation (opt-in, explicit user action only)

---

*Built for Hacktoberfest 2026 • Privacy-first • Local-first • Recommendation-only*