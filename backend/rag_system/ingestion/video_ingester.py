"""Video ingestion pipeline."""
from typing import Dict, Optional, List
from pathlib import Path
import cv2
from loguru import logger

from .base import BaseIngester
from .audio_ingester import AudioIngester


class VideoIngester(BaseIngester):
    """Ingester for video files (MP4, AVI)."""
    
    def __init__(self, frame_extraction_interval: int = 60):
        super().__init__()
        self.supported_formats = ["mp4", "avi"]
        # Increased interval to 60 seconds for faster processing (was 30)
        self.frame_extraction_interval = frame_extraction_interval
        self.audio_ingester = AudioIngester()
    
    def ingest(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Ingest a video file."""
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        path = Path(file_path)
        file_metadata = self.extract_metadata(file_path)
        if metadata:
            file_metadata.update(metadata)
        
        # Extract video information
        video_info = self._extract_video_info(path)
        file_metadata.update(video_info)
        
        # Extract frames
        frames = self._extract_frames(path)
        
        # Extract audio and transcribe
        audio_transcription = self._extract_audio_transcription(path)
        
        # Scene detection for video content
        scenes = self._detect_scenes(path)
        
        return {
            "content": {
                "frames": frames,
                "transcription": audio_transcription,
                "scenes": scenes,
                "video_path": str(path.absolute())
            },
            "metadata": file_metadata,
            "modality": "video",
            "chunks": self._create_video_chunks(frames, audio_transcription, scenes)
        }
    
    def _extract_video_info(self, path: Path) -> Dict:
        """Extract video metadata."""
        try:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                "video_fps": fps,
                "video_frame_count": frame_count,
                "video_width": width,
                "video_height": height,
                "video_duration_seconds": duration
            }
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return {}
    
    def _extract_frames(self, path: Path) -> List[Dict]:
        """Extract frames from video at intervals."""
        frames = []
        try:
            cap = cv2.VideoCapture(str(path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * self.frame_extraction_interval)
            
            frame_number = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_number % frame_interval == 0:
                    timestamp = frame_number / fps if fps > 0 else 0
                    # Save frame (in production, would save to storage)
                    frame_dir = Path("data/processed/frames")
                    frame_dir.mkdir(parents=True, exist_ok=True)
                    frame_path = str(frame_dir / f"{path.stem}_frame_{frame_number}.jpg")
                    cv2.imwrite(frame_path, frame)
                    
                    frames.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "frame_path": frame_path
                    })
                
                frame_number += 1
            
            cap.release()
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
        
        return frames
    
    def _extract_audio_transcription(self, path: Path) -> Dict:
        """Extract audio from video and transcribe."""
        try:
            # Extract audio from video
            import subprocess
            audio_dir = Path("data/processed/audio")
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = str(audio_dir / f"{path.stem}.wav")
            
            subprocess.run([
                "ffmpeg", "-i", str(path), "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", "-y", audio_path
            ], check=True, capture_output=True)
            
            # Transcribe using audio ingester
            return self.audio_ingester.ingest(audio_path)["content"]
        except Exception as e:
            logger.warning(f"Audio extraction/transcription failed: {e}")
            return {"transcription": "", "segments": []}
    
    def _detect_scenes(self, path: Path) -> List[Dict]:
        """Detect scene changes in video using histogram comparison."""
        scenes = []
        try:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                return []
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                cap.release()
                return []
            
            # Parameters for scene detection
            threshold = 0.3  # Histogram difference threshold (0-1)
            min_scene_length = 2.0  # Minimum scene length in seconds
            
            prev_hist = None
            scene_start = 0.0
            frame_number = 0
            scene_index = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                timestamp = frame_number / fps
                
                # Convert to HSV and calculate histogram
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1, 2], None, [50, 50, 50], [0, 180, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                if prev_hist is not None:
                    # Compare histograms using correlation
                    correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    difference = 1.0 - correlation
                    
                    # If difference exceeds threshold, it's a scene change
                    if difference > threshold:
                        scene_duration = timestamp - scene_start
                        # Only add scene if it's long enough
                        if scene_duration >= min_scene_length or scene_index == 0:
                            scenes.append({
                                "scene_index": scene_index,
                                "start_time": scene_start,
                                "end_time": timestamp,
                                "duration": scene_duration,
                                "start_frame": int(scene_start * fps),
                                "end_frame": frame_number
                            })
                            scene_index += 1
                            scene_start = timestamp
                
                prev_hist = hist
                frame_number += 1
            
            # Add final scene
            if scene_start < (frame_number / fps):
                final_timestamp = frame_number / fps
                scene_duration = final_timestamp - scene_start
                scenes.append({
                    "scene_index": scene_index,
                    "start_time": scene_start,
                    "end_time": final_timestamp,
                    "duration": scene_duration,
                    "start_frame": int(scene_start * fps),
                    "end_frame": frame_number
                })
            
            cap.release()
            logger.info(f"Detected {len(scenes)} scenes in video")
        except Exception as e:
            logger.warning(f"Scene detection failed: {e}")
            return []
        
        return scenes
    
    def _create_video_chunks(self, frames: List[Dict], transcription: Dict, scenes: List[Dict]) -> list:
        """Create chunks from video content."""
        chunks = []
        
        # Chunk by transcription segments
        segments = transcription.get("segments", [])
        for segment in segments:
            chunks.append({
                "text": segment.get("text", ""),
                "start": segment.get("start", 0),
                "end": segment.get("end", 0),
                "type": "audio_transcription"
            })
        
        # Add frame chunks
        for frame in frames:
            chunks.append({
                "frame_path": frame["frame_path"],
                "timestamp": frame["timestamp"],
                "type": "frame"
            })
        
        # Add scene chunks
        for scene in scenes:
            chunks.append({
                "text": f"Scene {scene.get('scene_index', 0)}: {scene.get('start_time', 0):.2f}s - {scene.get('end_time', 0):.2f}s (duration: {scene.get('duration', 0):.2f}s)",
                "start_time": scene.get("start_time", 0),
                "end_time": scene.get("end_time", 0),
                "duration": scene.get("duration", 0),
                "scene_index": scene.get("scene_index", 0),
                "type": "scene"
            })
        
        return chunks

