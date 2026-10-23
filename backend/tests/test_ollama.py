import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.ollama import classify_text, OllamaError
from app.models import OllamaSuggestion


class TestClassifyText:
    @pytest.mark.asyncio
    async def test_successful_classification(self):
        mock_response = {
            "response": json.dumps({
                "category": "Documents",
                "suggested_filename": "meeting-notes",
                "suggested_folder": "work",
                "explanation": "This appears to be meeting notes based on the agenda items.",
                "uncertainty": 0.1
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            result = await classify_text("Meeting agenda: 1. Project updates 2. Budget review")
            
            assert isinstance(result, OllamaSuggestion)
            assert result.category == "Documents"
            assert result.suggested_filename == "meeting-notes"
            assert result.suggested_folder == "work"
            assert result.uncertainty == 0.1
    
    @pytest.mark.asyncio
    async def test_model_not_found(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=404,
                text="Model not found"
            )
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert exc.value.status_code == 404
            assert "not found" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_connection_error(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "cannot connect" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_timeout(self):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "timed out" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        mock_response = {"response": "not valid json {"}
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "invalid json" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_suggestion_format(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
                "suggested_folder": "test",
                "explanation": "test",
                "uncertainty": 1.5
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "invalid suggestion format" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "../../../etc/passwd",
                "suggested_folder": "test",
                "explanation": "test",
                "uncertainty": 0.1
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "invalid suggestion format" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_absolute_path_rejected(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "/absolute/path",
                "suggested_folder": "test",
                "explanation": "test",
                "uncertainty": 0.1
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            with pytest.raises(OllamaError) as exc:
                await classify_text("test content")
            
            assert "invalid suggestion format" in exc.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            return MagicMock(
                status_code=200,
                json=lambda: {
                    "response": json.dumps({
                        "category": "Test",
                        "suggested_filename": "test",
                        "suggested_folder": "test",
                        "explanation": "test",
                        "uncertainty": 0.1
                    })
                }
            )
        
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            result = await classify_text("test content")
            assert call_count == 3
            assert isinstance(result, OllamaSuggestion)