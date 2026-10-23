import json
import httpx
from typing import Optional
from app.models import OllamaSuggestion
from app.config import get_settings


class OllamaError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


OLLAMA_PROMPT = """You are a file organization assistant. Analyze the provided file content and return a JSON object with the following fields:
- category: A brief category name (e.g., "Documents", "Code", "Notes", "Financial", "Personal")
- suggested_filename: A descriptive filename without extension, using only alphanumeric characters, hyphens, and underscores
- suggested_folder: A suggested folder name for organizing this file, using only alphanumeric characters, hyphens, and underscores
- explanation: A brief explanation (1-2 sentences) of why this categorization was chosen, grounded ONLY in the provided text
- uncertainty: A float between 0.0 and 1.0 indicating your confidence (0.0 = very uncertain, 1.0 = very certain)

IMPORTANT: 
- Base your analysis ONLY on the provided text content
- Do not claim to have inspected information not in the provided text
- Return ONLY valid JSON, no additional text or markdown

File content:
{text}"""


async def classify_text(text: str) -> OllamaSuggestion:
    settings = get_settings()
    
    prompt = OLLAMA_PROMPT.format(text=text)
    
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
        }
    }
    
    url = f"{settings.ollama_host}/api/generate"
    
    async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
        for attempt in range(settings.ollama_max_retries + 1):
            try:
                response = await client.post(url, json=payload)
                
                if response.status_code == 404:
                    raise OllamaError(
                        f"Ollama model '{settings.ollama_model}' not found. Pull it with: ollama pull {settings.ollama_model}",
                        status_code=404
                    )
                
                if response.status_code != 200:
                    raise OllamaError(
                        f"Ollama API error: {response.status_code} - {response.text[:200]}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                response_text = data.get("response", "").strip()
                
                if not response_text:
                    raise OllamaError("Empty response from Ollama")
                
                try:
                    parsed = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise OllamaError(f"Invalid JSON from Ollama: {e}")
                
                try:
                    suggestion = OllamaSuggestion(**parsed)
                    return suggestion
                except Exception as e:
                    raise OllamaError(f"Invalid suggestion format from Ollama: {e}")
            
            except httpx.TimeoutException:
                if attempt < settings.ollama_max_retries:
                    continue
                raise OllamaError(f"Ollama request timed out after {settings.ollama_timeout_seconds}s")
            
            except httpx.ConnectError:
                raise OllamaError(
                    f"Cannot connect to Ollama at {settings.ollama_host}. Is Ollama running?"
                )
            
            except OllamaError:
                raise
            
            except Exception as e:
                if attempt < settings.ollama_max_retries:
                    continue
                raise OllamaError(f"Unexpected error calling Ollama: {e}")
    
    raise OllamaError("Max retries exceeded")