"""Manager for coordinating multimodal ingestion."""
from typing import Dict, Optional
from pathlib import Path
from loguru import logger

from .base import BaseIngester
from .text_ingester import TextIngester
from .image_ingester import ImageIngester
from .audio_ingester import AudioIngester
from .video_ingester import VideoIngester
from ..utils.config import settings


class IngestionManager:
    """Manages ingestion of multiple file types."""
    
    def __init__(self):
        self.ingesters: Dict[str, BaseIngester] = {
            "text": TextIngester(),
            "image": ImageIngester(),
            "audio": AudioIngester(),
            "video": VideoIngester()
        }
    
    def ingest_file(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Ingest a file by automatically detecting its type.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata
        
        Returns:
            Dictionary with ingested content
        """
        path = Path(file_path)
        file_extension = path.suffix.lower().lstrip('.')
        
        # Determine file type
        file_type = self._determine_file_type(file_extension)
        
        if file_type not in self.ingesters:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        logger.info(f"Ingesting {file_type} file: {file_path}")
        
        try:
            result = self.ingesters[file_type].ingest(file_path, metadata)
            logger.info(f"Successfully ingested file: {file_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise
    
    def _determine_file_type(self, extension: str) -> Optional[str]:
        """Determine file type from extension."""
        if extension in settings.supported_text_formats:
            return "text"
        elif extension in settings.supported_image_formats:
            return "image"
        elif extension in settings.supported_audio_formats:
            return "audio"
        elif extension in settings.supported_video_formats:
            return "video"
        else:
            return None
    
    def validate_file(self, file_path: str):
        """Validate file and return (is_valid, error_message)."""
        path = Path(file_path)
        
        if not path.exists():
            return False, "File does not exist"
        
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            return False, f"File size ({file_size_mb:.2f} MB) exceeds maximum ({settings.max_file_size_mb} MB)"
        
        extension = path.suffix.lower().lstrip('.')
        file_type = self._determine_file_type(extension)
        
        if file_type is None:
            return False, f"Unsupported file format: {extension}"
        
        return True, None

