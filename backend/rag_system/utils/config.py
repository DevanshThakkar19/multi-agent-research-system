"""Configuration management for the multimodal RAG system."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_list(value: str) -> List[str]:
    """Parse comma-separated string into list."""
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return value if isinstance(value, list) else []


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env that aren't in the model
    )
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Updated to valid model
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # Smaller, cheaper model
    
    # Neo4j Configuration
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    
    # Qdrant Configuration
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "multimodal_rag")
    
    # System Configuration
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    
    # Security Configuration
    enable_security: bool = os.getenv("ENABLE_SECURITY", "true").lower() == "true"
    api_key: str = os.getenv("API_KEY", "")
    
    # List fields - parse from env or use defaults (not in Pydantic model to avoid parsing issues)
    @property
    def supported_image_formats(self) -> List[str]:
        return _parse_list(os.getenv("SUPPORTED_IMAGE_FORMATS", "jpg,jpeg,png"))
    
    @property
    def supported_audio_formats(self) -> List[str]:
        return _parse_list(os.getenv("SUPPORTED_AUDIO_FORMATS", "mp3,wav"))
    
    @property
    def supported_video_formats(self) -> List[str]:
        return _parse_list(os.getenv("SUPPORTED_VIDEO_FORMATS", "mp4,avi"))
    
    @property
    def supported_text_formats(self) -> List[str]:
        return _parse_list(os.getenv("SUPPORTED_TEXT_FORMATS", "pdf,txt,docx"))
    
    # Evaluation Configuration
    @property
    def eval_metrics(self) -> List[str]:
        return _parse_list(os.getenv("EVAL_METRICS", "precision,recall,latency,hallucination_rate"))
    
    @property
    def eval_query_types(self) -> List[str]:
        return _parse_list(os.getenv("EVAL_QUERY_TYPES", "lookup,summarization,semantic_linkages,reasoning"))


settings = Settings()

