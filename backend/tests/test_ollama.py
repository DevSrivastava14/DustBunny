import pytest
import json
import logging
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

    @pytest.mark.asyncio
    async def test_request_includes_think_false(self):
        """Verify that the Ollama request includes think: false to disable thinking mode."""
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
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
            
            await classify_text("test content")
            
            # Verify the request was called with think: false
            assert mock_post.called
            call_args = mock_post.call_args
            payload = call_args[1]["json"]  # kwargs['json']
            assert "think" in payload
            assert payload["think"] is False

    @pytest.mark.asyncio
    async def test_long_input_text_truncated(self):
        """Test that input text longer than max_analysis_text_chars is truncated before sending to Ollama."""
        long_text = "x" * 15000  # Exceeds default max_analysis_text_chars (8000)
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test",
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
            
            await classify_text(long_text)
            
            # Verify the request was called with truncated text in prompt
            assert mock_post.called
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            prompt = payload["prompt"]
            # The prompt should contain truncated text (max ~8000 chars + prompt template ~1500)
            assert len(prompt) < len(long_text) + 2000  # significantly shorter than original
            # The truncated text (8000 'x' chars) should appear in the prompt after the template
            assert "x" * 8000 in prompt

    @pytest.mark.asyncio
    async def test_timing_logged_on_success(self, caplog):
        """Test that timing is logged on successful classification."""
        mock_response = {
            "response": json.dumps({
                "category": "Test",
                "suggested_filename": "test-file",
                "suggested_folder": "test-folder",
                "explanation": "test explanation",
                "uncertainty": 0.1
            })
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response
            )
            
            with caplog.at_level(logging.INFO):
                await classify_text("test content")
            
            # Check that timing info was logged
            info_logs = [r for r in caplog.records if r.levelno >= logging.INFO]
            assert any("success" in r.message and "total_ms" in r.message for r in info_logs)
    
    @pytest.mark.asyncio
    async def test_timing_logged_on_timeout(self, caplog):
        """Test that timing is logged on timeout."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            with caplog.at_level(logging.WARNING):
                with pytest.raises(OllamaError):
                    await classify_text("test content")
            
            # Check that timeout timing was logged
            warning_logs = [r for r in caplog.records if r.levelno >= logging.WARNING]
            assert any("timeout" in r.message.lower() and "duration_ms" in r.message for r in warning_logs)


class TestOllamaSuggestionValidation:
    """Tests for OllamaSuggestion filename/folder validation."""
    
    def test_valid_filename_and_folder(self):
        suggestion = OllamaSuggestion(
            category="Test",
            suggested_filename="my-document",
            suggested_folder="work-files",
            explanation="Test explanation",
            uncertainty=0.1
        )
        assert suggestion.suggested_filename == "my-document"
        assert suggestion.suggested_folder == "work-files"
    
    def test_filename_with_underscore_and_dot(self):
        suggestion = OllamaSuggestion(
            category="Test",
            suggested_filename="my_document_v2",
            suggested_folder="work",
            explanation="Test",
            uncertainty=0.1
        )
        assert suggestion.suggested_filename == "my_document_v2"
    
    def test_filename_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="path traversal"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="../etc/passwd",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_absolute_path(self):
        with pytest.raises(ValueError, match="path traversal"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="/absolute/path",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_invalid_chars(self):
        with pytest.raises(ValueError, match="invalid characters"):
            OllamaSuggestion(
                category="Test",
                suggested_filename='file<name>',
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_colon(self):
        with pytest.raises(ValueError, match="invalid characters"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="file:name",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_leading_trailing_whitespace(self):
        with pytest.raises(ValueError, match="leading/trailing whitespace"):
            OllamaSuggestion(
                category="Test",
                suggested_filename=" filename",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_too_long(self):
        with pytest.raises(ValueError, match="at most 200 characters"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="a" * 201,
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_reserved_names(self):
        for reserved in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]:
            with pytest.raises(ValueError, match="reserved system name"):
                OllamaSuggestion(
                    category="Test",
                    suggested_filename=reserved,
                    suggested_folder="test",
                    explanation="Test",
                    uncertainty=0.1
                )
    
    def test_filename_rejects_reserved_with_extension(self):
        with pytest.raises(ValueError, match="reserved system name"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="CON.txt",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_no_alphanumeric(self):
        with pytest.raises(ValueError, match="must contain at least one alphanumeric"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="---",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_filename_rejects_invalid_chars_only_alphanumeric_hyphen_underscore_dot(self):
        with pytest.raises(ValueError, match="only alphanumeric"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="file@name",
                suggested_folder="test",
                explanation="Test",
                uncertainty=0.1
            )
    
    def test_folder_same_validation_as_filename(self):
        with pytest.raises(ValueError, match="path traversal"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="test",
                suggested_folder="../outside",
                explanation="Test",
                uncertainty=0.1
            )
        
        with pytest.raises(ValueError, match="at most 200 characters"):
            OllamaSuggestion(
                category="Test",
                suggested_filename="test",
                suggested_folder="a" * 201,
                explanation="Test",
                uncertainty=0.1
            )