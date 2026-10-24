import json
import httpx
from typing import Optional
from app.models import OllamaSuggestion
from app.config import get_settings


class OllamaError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, user_message: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.user_message = user_message or message
        super().__init__(message)


OLLAMA_PROMPT = """You are a file organization assistant. Analyze the provided file content and return a JSON object with the following fields:
- category: A brief category name (e.g., "Documents", "Code", "Notes", "Financial", "Personal")
- suggested_filename: A descriptive filename without extension, using only alphanumeric characters, hyphens, and underscores
- suggested_folder: A suggested folder name for organizing this file, using only alphanumeric characters, hyphens, and underscores
- explanation: A brief explanation (1-2 sentences) of why this categorization was chosen, grounded ONLY in the provided text
- uncertainty: A float between 0.0 and 1.0 indicating how UNCERTAIN you are about the categorization (0.0 = completely certain, 1.0 = completely uncertain). Base this on:
  * Text clarity and specificity: Clear, detailed content with obvious category indicators → lower uncertainty
  * Ambiguity or mixed topics: Vague, brief, or multi-topic content → higher uncertainty
  * Evidence strength: Strong keywords matching a single category → lower uncertainty; weak or conflicting signals → higher uncertainty
  * For a straightforward shopping list with clear items like "milk, eggs, bread" → uncertainty ~0.1-0.2
  * For a brief note with ambiguous content → uncertainty ~0.6-0.8
  * For contradictory or very sparse content → uncertainty ~0.8-1.0

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
                        status_code=404,
                        user_message=f"AI model '{settings.ollama_model}' not found. Please run: ollama pull {settings.ollama_model}"
                    )
                
                if response.status_code != 200:
                    raise OllamaError(
                        f"Ollama API error: {response.status_code} - {response.text[:200]}",
                        status_code=response.status_code,
                        user_message=f"AI service returned an error (code {response.status_code}). Please try again."
                    )
                
                data = response.json()
                response_text = data.get("response", "").strip()
                
                if not response_text:
                    raise OllamaError(
                        "Empty response from Ollama",
                        user_message="AI service returned an empty response. Please try again."
                    )
                
                try:
                    parsed = json.loads(response_text)
                except json.JSONDecodeError:
                    raise OllamaError(
                        "Invalid JSON from Ollama",
                        user_message="AI service returned an invalid response format. Please try again."
                    )
                
                try:
                    suggestion = OllamaSuggestion(**parsed)
                    return suggestion
                except Exception:
                    raise OllamaError(
                        "Invalid suggestion format from Ollama",
                        user_message="AI service returned an incomplete suggestion. Please try again."
                    )
            
            except httpx.TimeoutException:
                if attempt < settings.ollama_max_retries:
                    continue
                raise OllamaError(
                    f"Ollama request timed out after {settings.ollama_timeout_seconds}s",
                    user_message=f"AI request timed out after {settings.ollama_timeout_seconds} seconds. The model may be loading or overloaded. Please try again."
                )
            
            except httpx.ConnectError:
                raise OllamaError(
                    f"Cannot connect to Ollama at {settings.ollama_host}. Is Ollama running?",
                    user_message="Cannot connect to the local AI service. Please ensure Ollama is running (run 'ollama serve' in a terminal)."
                )
            
            except OllamaError:
                raise
            
            except Exception as e:
                if attempt < settings.ollama_max_retries:
                    continue
                raise OllamaError(
                    f"Unexpected error calling Ollama: {e}",
                    user_message="An unexpected error occurred while contacting the AI service. Please try again."
                )
    
    raise OllamaError(
        "Max retries exceeded",
        user_message="AI service did not respond after multiple attempts. Please try again later."
    )