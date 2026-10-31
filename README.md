# 🐰 DustBunny

### Your files deserve better than `Document1.pdf`.

**DustBunny is a privacy-first, local AI file organizer that analyzes your documents and suggests meaningful categories, filenames, and folder destinations — without automatically moving, renaming, or deleting anything.**

Powered by [Ollama](https://ollama.com/) and the open-weight `qwen3.5:2b` model, DustBunny brings AI-powered file organization directly to your machine.

No cloud AI services. No automatic file operations. No unnecessary complexity.

Just your files, your local AI, and recommendations that you control.

---

## 💡 The Problem

Over time, our computers accumulate hundreds or thousands of poorly organized files.

```text
Documents/
│
├── Document1.pdf
├── notes.txt
├── scan_20240115.pdf
├── meeting.md
├── final_v2.pdf
├── IMG_20240521.pdf
└── ...
```

Finding the right document becomes increasingly difficult.

Traditional file organization requires manually opening documents, understanding their contents, creating folders, and renaming files.

Cloud-based AI tools offer another approach, but they can require uploading personal documents to external services.

**What if your computer could organize its files intelligently without sending document contents to the cloud or changing your filesystem automatically?**

## 🐰 Meet DustBunny

DustBunny brings local AI into everyday file organization.

Select a folder, let the AI understand the contents of supported documents, and receive actionable organization recommendations.

For every successfully analyzed file, DustBunny can suggest:

- 📁 A meaningful category.
- 📝 A descriptive filename.
- 🗂️ An appropriate destination folder.
- 💬 A short explanation based on document content.
- 🎯 A confidence estimate reflecting the model's reported uncertainty.

Most importantly, **DustBunny never automatically moves, renames, or deletes your files.**

You remain in complete control of your filesystem.

## ✨ Features

| Feature | Description |
|---|---|
| 🔒 Local AI Inference | Uses Ollama to run the language model locally. |
| 📂 Folder Selection | Select a directory through the browser's folder picker. |
| 📝 Manual Path Entry | Analyze directories using a filesystem path through the backend. |
| 📄 Multiple File Formats | Supports `.txt`, `.md`, and `.pdf` files. |
| 📑 PDF Extraction | Extracts document text using PyMuPDF. |
| 🧠 AI Categorization | Suggests meaningful categories based on document contents. |
| ✏️ Smart File Renaming | Recommends descriptive filenames without automatically renaming files. |
| 🗂️ Folder Recommendations | Suggests appropriate destination folders. |
| 💬 Content-Based Explanations | Explains why a particular organization suggestion makes sense. |
| 🎯 Confidence Estimates | Converts model-reported uncertainty into a confidence percentage. |
| 📋 Copy to Clipboard | Copy suggested filenames and folder destinations. |
| 🌗 Dark & Light Themes | Supports system-based theme preferences. |
| 📱 Responsive Interface | Provides a responsive frontend experience. |
| 🛡️ Path Validation | Protects against path traversal and invalid or reserved names. |
| 🚫 Recommendation-Only Design | Never automatically modifies, moves, or deletes user files. |

## ⚙️ How It Works

DustBunny combines local document processing, a FastAPI backend, and Ollama-based AI inference.

### The Workflow

1. **Choose a folder:** Select a directory using the browser's folder picker or enter a filesystem path.
2. **Scan documents:** The backend identifies supported `.txt`, `.md`, and `.pdf` files.
3. **Extract content:** Text is extracted locally using direct text reading or PyMuPDF for PDFs.
4. **Analyze with local AI:** Extracted text is sent to your local Ollama instance running `qwen3.5:2b`.
5. **Generate recommendations:** The model returns structured suggestions for categories, filenames, folder destinations, explanations, and uncertainty.
6. **Review the results:** DustBunny displays the recommendations in an easy-to-understand interface.
7. **Take control:** Copy the suggestions you want to use. Your original files remain untouched.

### Typical Workflow

```text
Start Ollama
    |
    ▼
Select a Folder
    |
    ▼
Scan Supported Files
    |
    ▼
Extract Document Text
    |
    ▼
Local AI Analysis
    |
    ▼
Generate Organization Suggestions
    |
    ▼
Review & Copy Recommendations
    |
    ▼
You Decide What Happens Next
```

## 🔐 Privacy-First Architecture

Privacy is a core design decision, not an optional feature.

DustBunny is designed around local processing and local inference.

- Document scanning happens on your machine.
- PDF text extraction happens locally.
- AI inference uses your local Ollama server.
- Document contents are not intentionally sent to third-party cloud AI APIs.
- No telemetry or analytics services are included.
- No automatic file operations are performed.

### What Happens to Your Files?

| Operation | Behavior |
|---|---|
| Read document contents | Yes |
| Extract PDF text | Yes |
| Send text to local Ollama | Yes |
| Upload documents to cloud AI | No |
| Automatically rename files | No |
| Automatically move files | No |
| Automatically delete files | No |

**DustBunny is recommendation-only. Your original documents remain untouched by its organization workflow.**

The application sends extracted document text to the locally configured Ollama endpoint, normally `http://localhost:11434`.

## 🧠 The AI Model

DustBunny uses:

### `qwen3.5:2b` via Ollama

The project uses an open-weight, locally runnable language model rather than depending on a hosted commercial AI API.

| Component | Implementation |
|---|---|
| Model Runtime | Ollama |
| Model | `qwen3.5:2b` |
| Inference Location | Local machine |
| Communication | Local HTTP API |
| Generation Endpoint | Ollama `/api/generate` |
| Response Format | Structured JSON |
| Thinking Mode | Disabled using `think: false` |

### Why a Small Local Model?

The goal of DustBunny is to make AI-assisted organization practical on personal computers.

Using a smaller local model offers several advantages:

- No dependency on paid cloud inference.
- Document contents stay within the local processing workflow.
- The application can work without an external AI provider.
- Users can run the project with a locally downloaded model.

### An Important Optimization

During development, reasoning mode caused unnecessary latency and exposed thinking traces in model responses.

DustBunny sends:

```json
{
  "think": false
}
```

This disables thinking mode for the configured model requests.

In the development environment, this reduced a simple prompt's observed response time from approximately **77 seconds to 3.6 seconds**.

Actual performance varies with hardware, document length, system load, and the number of files being analyzed.

## 🏗️ Architecture

DustBunny follows a simple three-layer architecture.

```text
┌────────────────────────────┐
│       User Interface       │
│                            │
│       React 19 + Vite      │
│                            │
│  Folder Picker             │
│  Manual Path Entry         │
│  Results & Recommendations│
└──────────────┬─────────────┘
               │
               │ HTTP / JSON
               ▼
┌────────────────────────────┐
│       FastAPI Backend      │
│                            │
│  File Scanner              │
│  Text Extraction           │
│  Request Validation        │
│  AI Client                 │
│  Response Validation       │
└──────────────┬─────────────┘
               │
               │ Local HTTP
               ▼
┌────────────────────────────┐
│       Ollama Runtime       │
│                            │
│       qwen3.5:2b           │
│                            │
│  Document Understanding    │
│  Classification            │
│  Filename Suggestions      │
│  Folder Suggestions        │
└────────────────────────────┘
```

### Two Ways to Select Files

DustBunny supports two workflows.

| Method | How It Works |
|---|---|
| Browser Folder Picker | Uses the File System Access API to read supported files in the selected directory and send their contents to `/analyze-contents`. |
| Manual Folder Path | The backend scans the specified filesystem directory through `/analyze`. |

Both workflows return the same suggestion structure.

The browser folder picker requires a supported browser environment, normally HTTPS or localhost.

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 |
| Frontend Tooling | Vite |
| Styling | CSS Custom Properties |
| Backend | FastAPI 0.115 |
| Data Validation | Pydantic 2.9 |
| AI Runtime | Ollama |
| AI Model | `qwen3.5:2b` |
| PDF Processing | PyMuPDF |
| HTTP Client | HTTPX |
| Backend Testing | Pytest |
| Async Testing | Pytest-asyncio |
| Frontend Linting | Oxlint |

### Why These Technologies?

- **React + Vite:** Provides a modern, responsive user interface and fast development workflow.
- **FastAPI:** Handles file-analysis requests and coordinates backend processing.
- **Pydantic:** Validates request data and AI-generated recommendations.
- **Ollama:** Makes local language-model inference accessible without external AI services.
- **Qwen 3.5 2B:** Provides the local model used for document understanding and organization suggestions.
- **PyMuPDF:** Extracts text from PDF documents.
- **HTTPX:** Provides asynchronous communication with the local Ollama API.
- **Pytest:** Ensures predictable backend behavior through regression testing.

## 📂 Repository Structure

```text
AI Bunny/
│
├── .gitignore
├── .env.example
├── requirements.txt
├── progress.md
├── README.md
│
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── ollama.py
│   │   └── scanner.py
│   │
│   └── tests/
│       ├── test_analyze.py
│       ├── test_ollama.py
│       └── test_scanner.py
│
└── frontend/
    ├── public/
    │   ├── favicon.svg
    │   └── icons.svg
    │
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── App.css
        └── index.css
```

## 💻 Getting Started

Follow these steps to install and run DustBunny locally.

### Prerequisites

- Python 3.13 or newer.
- Node.js 20 or newer.
- npm.
- [Ollama](https://ollama.com/) installed and available in your system PATH.
- Sufficient memory and processing resources to run the selected local model.

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AI-Bunny
```

Replace the repository URL and directory name with your actual GitHub repository details.

### 2. Install Python Dependencies

From the repository root:

```bash
cd backend
python -m venv venv
```

**Windows:**

```powershell
.\venv\Scripts\activate
pip install -r ..\requirements.txt
```

**macOS / Linux:**

```bash
source venv/bin/activate
pip install -r ../requirements.txt
```

### 3. Download the AI Model

Pull the configured model:

```bash
ollama pull qwen3.5:2b
```

Verify that it is available:

```bash
ollama list
```

Make sure `qwen3.5:2b` appears in the installed model list.

### 4. Start Ollama

If Ollama is not already running, start its service:

```bash
ollama serve
```

Ollama normally listens on:

```text
http://localhost:11434
```

You can verify the available models using:

```text
http://localhost:11434/api/tags
```

### 5. Start the FastAPI Backend

From the `backend` directory, with the virtual environment activated:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will be available at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

### 6. Start the React Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

### 7. Analyze Your First Folder

1. Open DustBunny in your browser.
2. Click **Browse** to select a folder.
3. Alternatively, enter a folder path manually.
4. Click **Analyze**.
5. Wait for the local AI model to process the supported files.
6. Review the generated recommendations.
7. Copy the suggested filenames and folder destinations you want to use.

That's it! DustBunny is ready to help organize your documents.

## ⚙️ Configuration

### Backend Configuration

Backend settings are managed through `backend/app/config.py` and the environment configuration.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama server URL. |
| `OLLAMA_MODEL` | `qwen3.5:2b` | Model used for analysis. |
| `MAX_FILE_SIZE_MB` | `10` | Maximum supported file size per document. |
| `MAX_EXTRACTED_TEXT_CHARS` | `50000` | Maximum extracted text length per file. |
| `MAX_ANALYSIS_TEXT_CHARS` | `8000` | Maximum text length sent to the model. |
| `OLLAMA_TIMEOUT_SECONDS` | `60` | Per-request timeout. |
| `OLLAMA_MAX_RETRIES` | `2` | Maximum configured retry count. |

Longer documents are truncated before model inference to control input size.

### Frontend Configuration

The frontend uses:

```env
VITE_API_URL=http://127.0.0.1:8000
```

This configures the FastAPI backend URL.

## 🔌 API Documentation

DustBunny exposes two primary analysis endpoints.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Returns application information. |
| GET | `/health` | Backend health check. |
| POST | `/analyze` | Scans a folder using a backend filesystem path. |
| POST | `/analyze-contents` | Analyzes files whose contents were read by the browser. |

### POST `/analyze`

Analyzes a directory directly through the backend.

**Request:**

```json
{
  "folder_path": "C:/Users/me/Documents"
}
```

**Illustrative Response:**

```json
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

### POST `/analyze-contents`

Analyzes files selected through the browser folder picker.

**Request:**

```json
{
  "files": [
    {
      "filename": "notes.txt",
      "content": "Buy milk, eggs, bread"
    },
    {
      "filename": "document.pdf",
      "content_base64": "JVBERi0xLjQ..."
    }
  ]
}
```

Text and PDF contents are provided using their respective request fields.

For the complete API schema and interactive testing, visit:

```text
http://localhost:8000/docs
```

## 🛡️ Security & File Safety

DustBunny is designed to recommend filesystem organization without taking control away from the user.

### Path Validation

The backend validates paths and AI-generated organization suggestions to protect against unsafe filesystem operations.

Validation includes:

- Path traversal prevention.
- Rejection of absolute paths in suggested destinations.
- Windows reserved filename validation, including `CON`, `PRN`, and `COM1`.
- Validation of invalid filename and folder characters.
- Separation of filename and destination-folder validation.

### Document Processing Limits

| Limit | Value |
|---|---|
| Maximum file size | 10 MB |
| Maximum extracted text | 50,000 characters |
| Maximum text sent to model | 8,000 characters |
| Supported formats | TXT, MD, PDF |

These limits help control memory consumption and prevent unnecessarily large model requests.

### Recommendation-Only Design

DustBunny does not execute AI-generated file operations.

The model provides recommendations. The user decides whether to apply them manually.

## 🧪 Testing & Quality Assurance

DustBunny includes backend regression tests covering the scanner, API endpoints, Ollama integration, and model-output validation.

### Backend Tests

From the repository root:

```bash
python -m pytest backend/tests/ -v
```

**Verified test results:**

| Check | Result |
|---|---|
| Backend tests passed | 71 |
| Backend tests skipped | 2 |
| Frontend lint | Passed |
| Frontend production build | Passed |

The two skipped tests concern Windows symbolic-link behavior in the test environment.

### Frontend Linting

```bash
cd frontend
npm run lint
```

### Production Build

```bash
npm run build
```

The verified frontend lint run reported zero errors.

## ⚠️ Limitations

DustBunny is designed as a local, single-user recommendation tool. Some limitations are intentional trade-offs.

- **Sequential processing:** Files are analyzed one at a time. Total analysis time increases with the number of files.
- **Browser compatibility:** The File System Access API requires a supported browser and a secure context, normally HTTPS or localhost.
- **PDF processing:** Browser-selected PDFs are encoded in memory before being sent to the local backend.
- **Image-only PDFs:** Documents without extractable text may not produce useful recommendations.
- **Input truncation:** Only the first 8,000 characters of extracted text are sent to the model by default.
- **No analysis history:** Results are temporary and are not stored in a database.
- **No authentication:** The application is intended for local, single-user usage.
- **No cloud synchronization:** DustBunny does not provide cloud storage or cross-device synchronization.
- **Hardware dependency:** Model performance depends on available system resources and local Ollama performance.

## 🔧 Troubleshooting

| Problem | Possible Cause | Solution |
|---|---|---|
| Cannot reach backend | Backend is not running or incorrect API URL | Start FastAPI on port `8000` and verify the frontend API URL. |
| AI model not found | Model has not been downloaded | Run `ollama pull qwen3.5:2b`. |
| Ollama unavailable | Ollama service is not running | Start Ollama using `ollama serve` if necessary. |
| Incomplete suggestion | Model output is incomplete or fails validation | Check backend logs and try a smaller document. |
| PDF cannot be read | Corrupted or image-only PDF | Try a PDF containing extractable text. |
| Browser folder picker unavailable | Unsupported browser or insecure context | Use a supported browser on localhost or HTTPS, or use manual path entry. |
| Analysis takes a long time | Large number of files or sequential inference | Try a smaller folder or shorter documents. |
| Backend unavailable during analysis | Backend stopped or CORS configuration issue | Check backend logs and ensure the frontend origin is allowed. |

## 🤝 Contributing

Contributions are welcome!

If you would like to improve DustBunny:

1. Fork the repository.
2. Create a feature branch.
3. Implement your improvement.
4. Add or update relevant tests.
5. Run backend tests.
6. Run frontend linting and production build.
7. Submit a pull request explaining your contribution.

### Development Guidelines

- Keep changes small, focused, and maintainable.
- Avoid unnecessary dependencies.
- Preserve local-first inference.
- Preserve recommendation-only filesystem behavior.
- Maintain dark and light theme support.
- Include regression tests for behavior changes.

## 🗺️ Future Roadmap

The following are potential improvements, not currently implemented features.

- ⚡ Controlled parallel Ollama requests.
- 👀 File previews and content excerpts in result cards.
- 🖱️ Improved drag-and-drop folder selection.
- 💾 Local analysis history using IndexedDB.
- 🖥️ Desktop application packaging using Tauri or Electron.
- 📂 Optional batch rename and move operations with explicit user confirmation.

## 📜 License

No license file is currently present in this repository.

The project does not currently declare an open-source license. A license should be added before others redistribute, modify, or incorporate the code under an open-source license.

## 🏆 Hacktoberfest 2026

DustBunny was developed for the DEV/Hacktoberfest 2026 Open-Source AI challenge.

The project explores an important question:

**Can we make everyday AI genuinely useful without making users surrender control of their data or their devices?**

DustBunny approaches this through local inference, open-weight models, transparent recommendations, and a strict recommendation-only workflow.

Rather than automatically changing a user's filesystem, it provides intelligent suggestions and leaves the final decision to the person using it.

## 🙏 Acknowledgements

DustBunny is built with the help of:

- [React](https://react.dev/) — Frontend library.
- [Vite](https://vite.dev/) — Frontend tooling.
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework.
- [Pydantic](https://docs.pydantic.dev/) — Data validation.
- [Ollama](https://ollama.com/) — Local AI model runtime.
- [Qwen](https://qwen.ai/) — Open-weight model family.
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF text extraction.
- [HTTPX](https://www.python-httpx.org/) — Asynchronous HTTP client.
- [Pytest](https://pytest.org/) — Testing framework.

---

<p align="center">
  <b>🐰 DustBunny — A little less mess. A lot more intelligence.</b>
  <br/>
  <i>Local-first. Privacy-first. Always under your control.</i>
  <br/><br/>
  ⭐ If DustBunny makes file organization easier, consider starring the repository!
</p>