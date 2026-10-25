import pytest
from pathlib import Path
import tempfile
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models import FileStatus, OllamaSuggestion


client = TestClient(app)


def make_suggestion(category: str, filename: str, folder: str, explanation: str, uncertainty: float) -> OllamaSuggestion:
    return OllamaSuggestion(
        category=category,
        suggested_filename=filename,
        suggested_folder=folder,
        explanation=explanation,
        uncertainty=uncertainty
    )


class TestAnalyzeEndpoint:
    def test_analyze_nonexistent_folder(self):
        response = client.post("/analyze", json={"folder_path": "/nonexistent"})
        assert response.status_code == 400
        assert "does not exist" in response.json()["detail"]
    
    def test_analyze_file_instead_of_folder(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("content")
        response = client.post("/analyze", json={"folder_path": str(file_path)})
        assert response.status_code == 400
        assert "not a directory" in response.json()["detail"]
    
    def test_analyze_empty_folder(self, tmp_path):
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Test", "test", "test", "test", 0.1)
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 0
        assert data["processed_files"] == 0
        assert data["results"] == []
    
    def test_analyze_with_txt_files(self, tmp_path):
        (tmp_path / "doc1.txt").write_text("Meeting notes: Discussed project timeline and budget.")
        (tmp_path / "doc2.txt").write_text("Shopping list: Milk, eggs, bread.")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.side_effect = [
                make_suggestion("Work", "meeting-notes", "projects", "Contains meeting agenda items about project and budget.", 0.1),
                make_suggestion("Personal", "shopping-list", "personal", "List of grocery items to buy.", 0.05),
            ]
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        assert data["processed_files"] == 2
        assert data["skipped_files"] == 0
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "success"
        assert data["results"][0]["suggestion"]["category"] == "Work"
        assert data["results"][1]["suggestion"]["category"] == "Personal"
    
    def test_analyze_skips_unsupported_files(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Text content")
        (tmp_path / "image.jpg").write_bytes(b"fake")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Test", "test", "test", "test", 0.1)
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        assert data["processed_files"] == 1
        assert data["skipped_files"] == 1
        statuses = {r["status"] for r in data["results"]}
        assert "success" in statuses
        assert "skipped_unsupported" in statuses
    
    def test_analyze_handles_ollama_error(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Content")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            from app.ollama import OllamaError
            mock_classify.side_effect = OllamaError("Model not available", status_code=503, user_message="AI service temporarily unavailable")
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["error_files"] == 1
        assert data["results"][0]["status"] == "error"
        assert "AI service temporarily unavailable" in data["results"][0]["error_message"]

    def test_analyze_ollama_connection_error_message(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Content")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            from app.ollama import OllamaError
            mock_classify.side_effect = OllamaError(
                "Cannot connect to Ollama at http://localhost:11434",
                user_message="Cannot connect to the local AI service. Please ensure Ollama is running (run 'ollama serve' in a terminal)."
            )
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_files"] == 1
        assert "Cannot connect to the local AI service" in data["results"][0]["error_message"]
        assert "ollama serve" in data["results"][0]["error_message"]

    def test_analyze_ollama_timeout_error_message(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Content")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            from app.ollama import OllamaError
            mock_classify.side_effect = OllamaError(
                "Ollama request timed out after 60s",
                user_message="AI request timed out after 60 seconds. The model may be loading or overloaded. Please try again."
            )
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_files"] == 1
        assert "timed out" in data["results"][0]["error_message"].lower()
        assert "try again" in data["results"][0]["error_message"].lower()

    def test_analyze_ollama_model_not_found_message(self, tmp_path):
        (tmp_path / "doc.txt").write_text("Content")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            from app.ollama import OllamaError
            mock_classify.side_effect = OllamaError(
                "Ollama model 'qwen3.5:2b' not found",
                status_code=404,
                user_message="AI model 'qwen3.5:2b' not found. Please run: ollama pull qwen3.5:2b"
            )
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_files"] == 1
        assert "qwen3.5:2b" in data["results"][0]["error_message"]
        assert "ollama pull" in data["results"][0]["error_message"]
    
    def test_analyze_pdf_file(self, tmp_path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Invoice #12345\nAmount: $100.00\nDate: 2024-01-15")
        pdf_path = tmp_path / "invoice.pdf"
        doc.save(str(pdf_path))
        doc.close()
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Financial", "invoice-12345", "finance", "Contains invoice details with amount and date.", 0.05)
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 1
        assert data["results"][0]["filename"] == "invoice.pdf"
        assert data["results"][0]["suggestion"]["category"] == "Financial"
    
    def test_response_structure(self, tmp_path):
        (tmp_path / "test.txt").write_text("Test content")
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Test", "test-file", "test-folder", "Test explanation", 0.2)
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["folder_path", "total_files", "processed_files", "skipped_files", "error_files", "results"]
        for field in required_fields:
            assert field in data
        
        result = data["results"][0]
        assert "filename" in result
        assert "status" in result
        assert "suggestion" in result
        
        suggestion = result["suggestion"]
        assert "category" in suggestion
        assert "suggested_filename" in suggestion
        assert "suggested_folder" in suggestion
        assert "explanation" in suggestion
        assert "uncertainty" in suggestion


class TestAnalyzeContentsEndpoint:
    def test_analyze_contents_success(self):
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.side_effect = [
                make_suggestion("Work", "meeting-notes", "projects", "Meeting notes about project.", 0.1),
                make_suggestion("Personal", "shopping-list", "personal", "Grocery list.", 0.05),
            ]
            response = client.post("/analyze-contents", json={
                "files": [
                    {"filename": "notes.txt", "content": "Meeting notes: Discuss project timeline."},
                    {"filename": "list.md", "content": "# Shopping List\n- Milk\n- Eggs"},
                ]
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        assert data["processed_files"] == 2
        assert data["skipped_files"] == 0
        assert data["error_files"] == 0
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "success"
        assert data["results"][0]["suggestion"]["category"] == "Work"
        assert data["results"][1]["suggestion"]["category"] == "Personal"
        assert data["folder_path"] == "browser-selected-folder"
    
    def test_analyze_contents_skips_unsupported(self):
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Test", "test", "test", "test", 0.1)
            response = client.post("/analyze-contents", json={
                "files": [
                    {"filename": "doc.txt", "content": "Text content"},
                    {"filename": "image.jpg", "content": "fake"},
                    {"filename": "doc.pdf", "content": "PDF content"},
                ]
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 3
        assert data["processed_files"] == 1
        assert data["skipped_files"] == 2
        statuses = {r["status"] for r in data["results"]}
        assert "success" in statuses
        assert "skipped_unsupported" in statuses
    
    def test_analyze_contents_skips_empty(self):
        response = client.post("/analyze-contents", json={
            "files": [
                {"filename": "empty.txt", "content": ""},
                {"filename": "empty.md", "content": "   "},
            ]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 2
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 2
        for r in data["results"]:
            assert r["status"] == "skipped_empty"
    
    def test_analyze_contents_handles_ollama_error(self):
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            from app.ollama import OllamaError
            mock_classify.side_effect = OllamaError("Model not available", status_code=503, user_message="AI service temporarily unavailable")
            response = client.post("/analyze-contents", json={
                "files": [{"filename": "doc.txt", "content": "Content"}]
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["error_files"] == 1
        assert data["results"][0]["status"] == "error"
        assert "AI service temporarily unavailable" in data["results"][0]["error_message"]
    
    def test_analyze_contents_requires_files(self):
        response = client.post("/analyze-contents", json={"files": []})
        assert response.status_code == 422
    
    def test_analyze_contents_requires_filename_and_content(self):
        # With new model, content defaults to "" for txt/md (handled as SKIPPED_EMPTY)
        response = client.post("/analyze-contents", json={"files": [{"filename": "test.txt"}]})
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        assert data["results"][0]["status"] == "skipped_empty"
        
        # PDF without content_base64 should be skipped as unsupported
        response = client.post("/analyze-contents", json={"files": [{"filename": "test.pdf"}]})
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        assert data["results"][0]["status"] == "skipped_unsupported"
        
        # Missing filename should still fail validation
        response = client.post("/analyze-contents", json={"files": [{"content": "test"}]})
        assert response.status_code == 422
    
    def test_analyze_contents_pdf_success(self):
        """Test successful PDF upload and processing."""
        # Create a PDF with actual text content
        import fitz
        import base64
        import io
        
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Invoice #12345\nAmount: $100.00\nDate: 2024-01-15")
        pdf_stream = io.BytesIO()
        doc.save(pdf_stream)
        doc.close()
        pdf_b64 = base64.b64encode(pdf_stream.getvalue()).decode()
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = make_suggestion("Financial", "invoice-12345", "finance", "Invoice document", 0.1)
            response = client.post("/analyze-contents", json={
                "files": [{"filename": "invoice.pdf", "content_base64": pdf_b64}]
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 1
        assert data["skipped_files"] == 0
        assert data["results"][0]["status"] == "success"
    
    def test_analyze_contents_pdf_corrupted(self):
        """Test corrupted PDF handling."""
        import base64
        corrupted_pdf = base64.b64encode(b"not a pdf").decode()
        
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "corrupted.pdf", "content_base64": corrupted_pdf}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        assert data["results"][0]["status"] == "skipped_unreadable"
    
    def test_analyze_contents_pdf_encrypted(self):
        """Test encrypted PDF handling."""
        import fitz
        import base64
        import io
        
        # Create an encrypted PDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Secret content")
        pdf_stream = io.BytesIO()
        doc.save(pdf_stream, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="password", owner_pw="password")
        doc.close()
        pdf_b64 = base64.b64encode(pdf_stream.getvalue()).decode()
        
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "encrypted.pdf", "content_base64": pdf_b64}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        assert data["results"][0]["status"] == "skipped_encrypted"
    
    def test_analyze_contents_pdf_oversized(self):
        """Test oversized PDF rejection."""
        import base64
        # Create a fake large PDF (over 10MB)
        large_pdf = base64.b64encode(b"x" * (11 * 1024 * 1024)).decode()
        
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "large.pdf", "content_base64": large_pdf}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        assert data["results"][0]["status"] == "skipped_oversized"
    
    def test_analyze_contents_pdf_empty(self):
        """Test empty PDF handling (no extractable text)."""
        import base64
        empty_pdf = base64.b64encode(b"").decode()
        
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "empty.pdf", "content_base64": empty_pdf}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["skipped_files"] == 1
        # Empty PDF bytes are caught before PDF parsing
        assert data["results"][0]["status"] == "skipped_empty"
    
    def test_analyze_contents_mixed_types(self):
        """Test mixed TXT, MD, and PDF files in one request."""
        import fitz
        import base64
        import io
        
        # Create a PDF with text content
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF document content")
        pdf_stream = io.BytesIO()
        doc.save(pdf_stream)
        doc.close()
        pdf_b64 = base64.b64encode(pdf_stream.getvalue()).decode()
        
        with patch("app.main.classify_text", new_callable=AsyncMock) as mock_classify:
            mock_classify.side_effect = [
                make_suggestion("Notes", "notes", "notes", "Text note", 0.1),
                make_suggestion("Documents", "doc", "docs", "Markdown doc", 0.1),
                make_suggestion("Documents", "pdfdoc", "docs", "PDF document", 0.1),
            ]
            response = client.post("/analyze-contents", json={
                "files": [
                    {"filename": "notes.txt", "content": "Some notes"},
                    {"filename": "doc.md", "content": "# Markdown"},
                    {"filename": "doc.pdf", "content_base64": pdf_b64},
                ]
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 3
        assert data["processed_files"] == 3
        assert data["skipped_files"] == 0
    
    def test_analyze_contents_path_traversal_rejected(self):
        """Test path traversal in filename is rejected."""
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "../etc/passwd", "content": "malicious"}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["error_files"] == 1
        assert data["results"][0]["status"] == "error"
        assert "path traversal" in data["results"][0]["error_message"].lower()
        
        # Also test absolute path
        response = client.post("/analyze-contents", json={
            "files": [{"filename": "/absolute/path.txt", "content": "test"}]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["status"] == "error"
        assert "path traversal" in data["results"][0]["error_message"].lower() or "absolute" in data["results"][0]["error_message"].lower()