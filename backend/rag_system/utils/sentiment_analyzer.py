"""Sentiment detection for text and audio."""
from typing import Dict, Optional
from loguru import logger

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    logger.warning("TextBlob not available. Sentiment analysis will be disabled.")


class SentimentAnalyzer:
    """Analyze sentiment in text and audio transcriptions."""
    
    def __init__(self):
        self.available = TEXTBLOB_AVAILABLE
        if not self.available:
            logger.warning("Sentiment analysis disabled: TextBlob not installed")
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Dictionary with polarity and subjectivity scores
        """
        if not self.available or not text:
            return {
                "polarity": 0.0,
                "subjectivity": 0.0,
                "sentiment": "neutral"
            }
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Classify sentiment
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "polarity": float(polarity),
                "subjectivity": float(subjectivity),
                "sentiment": sentiment
            }
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {
                "polarity": 0.0,
                "subjectivity": 0.0,
                "sentiment": "neutral"
            }
    
    def extract_sentiment_metadata(self, content: Dict) -> Dict:
        """
        Extract sentiment metadata from ingested content.
        
        Args:
            content: Ingested content dictionary
        
        Returns:
            Content with added sentiment metadata
        """
        if not self.available:
            return content
        
        # Extract text based on modality
        text = ""
        if isinstance(content.get("content"), dict):
            if "transcription" in content["content"]:
                transcription = content["content"]["transcription"]
                # Handle transcription as dict (video/audio) or string
                if isinstance(transcription, dict):
                    text = transcription.get("text", "")
                elif isinstance(transcription, str):
                    text = transcription
            elif "text" in content["content"]:
                text = content["content"]["text"]
        elif isinstance(content.get("content"), str):
            text = content["content"]
        
        # Ensure text is a string before analyzing
        if text and isinstance(text, str):
            sentiment = self.analyze_sentiment(text)
            if "metadata" not in content:
                content["metadata"] = {}
            content["metadata"]["sentiment"] = sentiment
        
        return content


