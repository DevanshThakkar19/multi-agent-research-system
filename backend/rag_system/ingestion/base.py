"""Base class for ingestion pipelines."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import hashlib
from loguru import logger


class BaseIngester(ABC):
    """Base class for all ingestion pipelines."""
    
    def __init__(self):
        self.supported_formats = []
    
    @abstractmethod
    def ingest(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Ingest a file and return processed content.
        
        Args:
            file_path: Path to the file
            metadata: Optional metadata about the file
        
        Returns:
            Dictionary with processed content and metadata
        """
        pass
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that the file exists and is in a supported format."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        if path.suffix.lower().lstrip('.') not in self.supported_formats:
            logger.error(f"Unsupported format: {path.suffix}")
            return False
        
        return True
    
    def generate_file_id(self, file_path: str) -> str:
        """Generate a unique ID for the file."""
        path = Path(file_path)
        file_hash = hashlib.md5(f"{path.name}{path.stat().st_size}".encode()).hexdigest()
        return f"{path.stem}_{file_hash[:8]}"
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract basic metadata from file."""
        path = Path(file_path)
        return {
            "file_name": path.name,
            "file_path": str(path.absolute()),
            "file_size": path.stat().st_size,
            "file_format": path.suffix.lower().lstrip('.'),
            "ingestion_timestamp": datetime.now().isoformat(),
            "file_id": self.generate_file_id(file_path)
        }

