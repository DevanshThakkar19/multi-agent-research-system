"""Image ingestion pipeline."""
from typing import Dict, Optional
from pathlib import Path
from PIL import Image
import pytesseract
from loguru import logger

from .base import BaseIngester


class ImageIngester(BaseIngester):
    """Ingester for image files (JPG, PNG)."""
    
    def __init__(self):
        super().__init__()
        self.supported_formats = ["jpg", "jpeg", "png"]
    
    def ingest(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Ingest an image file."""
        if not self.validate_file(file_path):
            raise ValueError(f"Invalid file: {file_path}")
        
        path = Path(file_path)
        file_metadata = self.extract_metadata(file_path)
        if metadata:
            file_metadata.update(metadata)
        
        # Extract image properties
        image_info = self._extract_image_info(path)
        file_metadata.update(image_info)
        
        # Perform OCR
        ocr_text = self._perform_ocr(path)
        
        # Generate caption (placeholder - would use LLaVA or similar)
        caption = self._generate_caption(path)
        
        return {
            "content": {
                "ocr_text": ocr_text,
                "caption": caption,
                "image_path": str(path.absolute())
            },
            "metadata": file_metadata,
            "modality": "image",
            "chunks": [{"text": ocr_text, "caption": caption}]
        }
    
    def _extract_image_info(self, path: Path) -> Dict:
        """Extract basic image information."""
        try:
            with Image.open(path) as img:
                return {
                    "image_width": img.width,
                    "image_height": img.height,
                    "image_format": img.format,
                    "image_mode": img.mode
                }
        except Exception as e:
            logger.error(f"Error extracting image info: {e}")
            return {}
    
    def _perform_ocr(self, path: Path) -> str:
        """Perform OCR on image."""
        try:
            text = pytesseract.image_to_string(path)
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""
    
    def _generate_caption(self, path: Path) -> str:
        """Generate caption for image using vision model or OCR fallback."""
        # Try to use OCR text as caption if available
        ocr_text = self._perform_ocr(path)
        if ocr_text and len(ocr_text.strip()) > 10:
            # Use OCR text as caption if substantial text found
            return ocr_text[:200]  # Limit length
        
        # Fallback: try OpenAI vision API if available
        try:
            import base64
            from openai import OpenAI
            from ..utils.config import settings
            
            if settings.openai_api_key:
                client = OpenAI(api_key=settings.openai_api_key)
                with open(path, "rb") as image_file:
                    # Encode image to base64
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    image_format = path.suffix[1:].lower()  # Get format without dot
                    mime_type = f"image/{image_format}" if image_format in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else "image/png"
                    
                    # Try vision-capable models in order
                    vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
                    response = None
                    last_error = None
                    
                    for model in vision_models:
                        try:
                            response = client.chat.completions.create(
                                model=model,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": "Describe this image in detail, including any text, numbers, charts, or data visible in it. Be specific about any statistics or information shown."},
                                            {
                                                "type": "image_url",
                                                "image_url": {
                                                    "url": f"data:{mime_type};base64,{image_data}"
                                                }
                                            }
                                        ]
                                    }
                                ],
                                max_tokens=500
                            )
                            break  # Success, exit loop
                        except Exception as e:
                            last_error = e
                            continue  # Try next model
                    
                    if response:
                        caption = response.choices[0].message.content
                        logger.info(f"Generated caption using Vision API: {len(caption)} characters")
                        return caption
                    else:
                        raise last_error if last_error else Exception("No vision model available")
        except Exception as e:
            logger.warning(f"Vision API caption failed: {e}")
        
        # Final fallback
        return f"Image file: {path.name}"

