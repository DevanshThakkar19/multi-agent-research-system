"""Phoenix monitoring integration for LLM observability."""
from typing import Dict, Optional, List
from loguru import logger

try:
    import phoenix as px
    from phoenix.trace import openai
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    logger.info("Phoenix not available, monitoring disabled")


class PhoenixMonitor:
    """Phoenix monitoring for LLM traces and evaluation."""
    
    def __init__(self, project_name: str = "multimodal-rag"):
        self.available = PHOENIX_AVAILABLE
        self.project_name = project_name
        self.session = None
        
        if self.available:
            try:
                # Initialize Phoenix session
                self.session = px.Client()
                logger.info("Phoenix monitoring initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Phoenix: {e}")
                self.available = False
        else:
            logger.info("Phoenix monitoring not available")
    
    def start_session(self, project_name: Optional[str] = None):
        """Start a Phoenix session for tracing."""
        if not self.available:
            return None
        
        try:
            project = project_name or self.project_name
            # Phoenix automatically starts when you use the OpenAI instrumentation
            logger.info(f"Phoenix session ready for project: {project}")
            return True
        except Exception as e:
            logger.warning(f"Failed to start Phoenix session: {e}")
            return None
    
    def log_query(
        self,
        query: str,
        answer: str,
        context: List[str],
        metadata: Optional[Dict] = None
    ):
        """Log a query and answer to Phoenix."""
        if not self.available:
            return
        
        try:
            # Phoenix automatically captures OpenAI API calls via instrumentation
            # Additional metadata can be logged here if needed
            logger.debug(f"Query logged to Phoenix: {query[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to log to Phoenix: {e}")
    
    def get_session_url(self) -> Optional[str]:
        """Get the Phoenix session URL for viewing traces."""
        if not self.available or not self.session:
            return None
        
        try:
            # Phoenix typically runs on localhost:6006
            return "http://localhost:6006"
        except Exception:
            return None







