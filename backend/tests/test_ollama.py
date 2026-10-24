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
    async def test_invalid_characters_in_filename_rejected(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "file<name>",
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
    async def test_backslash_path_traversal_rejected(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "..\\..\\windows\\system32",
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
    async def test_colon_in_folder_rejected(self):
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
                "suggested_folder": "folder:name",
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
    async def test_user_message_in_error(self):
        error = OllamaError("internal detail", status_code=500, user_message="User friendly message")
        assert error.user_message == "User friendly message"
    
    @pytest.mark.asyncio
    async def test_user_message_defaults_to_message(self):
        error = OllamaError("internal detail", status_code=500)
        assert error.user_message == "internal detail"
    
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

    @pytest.mark.asyncio
    async def test_uncertainty_to_confidence_calculation(self):
        """Test that uncertainty 0.90 displays as 10% confidence and 0.10 as 90%."""
        # Test uncertainty 0.90 -> 10% confidence
        mock_response_high_uncertainty = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
                "suggested_folder": "test",
                "explanation": "test",
                "uncertainty": 0.90
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response_high_uncertainty
            )
            
            result = await classify_text("test content")
            assert result.uncertainty == 0.90
            # Frontend calculates: (1 - 0.90) * 100 = 10%
            confidence = (1 - result.uncertainty) * 100
            assert abs(confidence - 10.0) < 0.001
        
        # Test uncertainty 0.10 -> 90% confidence
        mock_response_low_uncertainty = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
                "suggested_folder": "test",
                "explanation": "test",
                "uncertainty": 0.10
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response_low_uncertainty
            )
            
            result = await classify_text("test content")
            assert result.uncertainty == 0.10
            # Frontend calculates: (1 - 0.10) * 100 = 90%
            confidence = (1 - result.uncertainty) * 100
            assert abs(confidence - 90.0) < 0.001