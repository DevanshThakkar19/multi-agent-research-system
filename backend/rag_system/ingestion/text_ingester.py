"""Text ingestion pipeline."""
from typing import Dict, Optional
from pathlib import Path
import pdfplumber
from loguru import logger

from .base import BaseIngester

# Try to import Chonkie for advanced document processing
try:
    from chonkie import Chonkie
    CHONKIE_AVAILABLE = True
except ImportError:
    CHONKIE_AVAILABLE = False
    logger.info("Chonkie not available, using fallback PDF processing")


class TextIngester(BaseIngester):
    """Ingester for text files (PDF, TXT, DOCX)."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ["pdf", "txt", "docx"]
    
    def ingest(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Ingest a text file."""
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        path = Path(file_path)
        file_metadata = self.extract_metadata(file_path)
        if metadata:
            file_metadata.update(metadata)
        
        content = self._extract_text(path)
        
        return {
            "content": content,
            "metadata": file_metadata,
            "modality": "text",
            "chunks": self._chunk_text(content)
        }
    
    def _extract_text(self, path: Path) -> str:
        """Extract text from file based on format."""
        if path.suffix.lower() == ".pdf":
            return self._extract_from_pdf(path)
        elif path.suffix.lower() == ".txt":
            return self._extract_from_txt(path)
        elif path.suffix.lower() == ".docx":
            return self._extract_from_docx(path)
        else:
            raise ValueError(f"Unsupported text format: {path.suffix}")
    
    def _extract_from_pdf(self, path: Path) -> str:
        """Extract text from PDF using Chonkie (if available) or pdfplumber fallback."""
        try:
            # Try Chonkie first for better layout understanding
            if CHONKIE_AVAILABLE:
                try:
                    chonkie = Chonkie()
                    result = chonkie.parse(str(path))
                    
                    # Extract text with layout information
                    text_parts = []
                    if hasattr(result, 'pages'):
                        for page in result.pages:
                            if hasattr(page, 'text'):
                                text_parts.append(page.text)
                            elif hasattr(page, 'elements'):
                                # Extract text from elements
                                page_text = []
                                for element in page.elements:
                                    if hasattr(element, 'text'):
                                        page_text.append(element.text)
                                text_parts.append("\n".join(page_text))
                    
                    if text_parts:
                        logger.info(f"Successfully extracted PDF using Chonkie: {len(text_parts)} pages")
                        return "\n\n".join(text_parts)
                except Exception as e:
                    logger.warning(f"Chonkie extraction failed, falling back to pdfplumber: {e}")
            
            # Fallback to pdfplumber
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise
    
    def _extract_from_txt(self, path: Path) -> str:
        """Extract text from TXT file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading TXT file: {e}")
            raise
    
    def _extract_from_docx(self, path: Path) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
            doc = Document(path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
        """Split text into chunks for processing."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append({
                "text": chunk,
                "start_index": i,
                "end_index": min(i + chunk_size, len(words))
            })
        
        return chunks

