"""Audio ingestion pipeline."""
from typing import Dict, Optional
from pathlib import Path
from loguru import logger

from .base import BaseIngester

# Try to import whisper, but make it optional
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Audio transcription will be disabled.")


class AudioIngester(BaseIngester):
    """Ingester for audio files (MP3, WAV)."""
    
    def __init__(self, model_size: str = "base"):
        super().__init__()
        self.supported_formats = ["mp3", "wav"]
        self.model_size = model_size
        self._model = None
    
    def _load_model(self):
        """Lazy load Whisper model."""
        if not WHISPER_AVAILABLE:
            raise ImportError("Whisper is not installed. Install with: pip install openai-whisper")
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = whisper.load_model(self.model_size)
        return self._model
    
    def ingest(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Ingest an audio file."""
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        path = Path(file_path)
        file_metadata = self.extract_metadata(file_path)
        if metadata:
            file_metadata.update(metadata)
        
        # Transcribe audio
        transcription = self._transcribe_audio(path)
        
        # Extract metadata from audio
        audio_info = self._extract_audio_info(path)
        file_metadata.update(audio_info)
        
        return {
            "content": {
                "transcription": transcription["text"],
                "segments": transcription.get("segments", []),
                "language": transcription.get("language", "unknown")
            },
            "metadata": file_metadata,
            "modality": "audio",
            "chunks": self._chunk_transcription(transcription)
        }
    
    def _transcribe_audio(self, path: Path) -> Dict:
        """Transcribe audio using Whisper."""
        try:
            model = self._load_model()
            result = model.transcribe(str(path))
            return result
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def _extract_audio_info(self, path: Path) -> Dict:
        """Extract audio file information."""
        # Placeholder - would use librosa or similar
        return {
            "audio_format": path.suffix.lower().lstrip('.')
        }
    
    def _chunk_transcription(self, transcription: Dict) -> list:
        """Chunk transcription into segments."""
        chunks = []
        segments = transcription.get("segments", [])
        
        for segment in segments:
            chunks.append({
                "text": segment.get("text", ""),
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "confidence": segment.get("no_speech_prob", 0)
            })
        
        return chunks

