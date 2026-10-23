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
            mock_classify.side_effect = OllamaError("Model not available", status_code=503)
            response = client.post("/analyze", json={"folder_path": str(tmp_path)})
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 1
        assert data["processed_files"] == 0
        assert data["error_files"] == 1
        assert data["results"][0]["status"] == "error"
        assert "AI classification failed" in data["results"][0]["error_message"]
    
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