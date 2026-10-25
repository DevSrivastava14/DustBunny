import os
from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_reload: bool = True
    
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:2b"
    
    max_file_size_mb: int = 10
    max_extracted_text_chars: int = 50000
    max_analysis_text_chars: int = 8000
    scan_timeout_seconds: int = 30
    
    ollama_timeout_seconds: int = 60
    ollama_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()