"""
Document Analyzer Agent
Integrates with the RAG system to query uploaded documents.
"""

from typing import Dict, Any, List
import logging
import sys
import os

# Add RAG system to path
rag_system_path = os.path.join(os.path.dirname(__file__), '..', 'rag_system')
if rag_system_path not in sys.path:
    sys.path.insert(0, rag_system_path)

from core.agent_base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class DocumentAnalyzerAgent(BaseAgent):
    """
    Analyzes documents using the integrated RAG system.
    Queries the knowledge base for relevant information from uploaded documents.
    """
    
    def __init__(self):
        super().__init__(
            name="document_analyzer",
            description="Queries uploaded documents using the RAG system to extract relevant information"
        )
        self.rag_pipeline = None
        self.rag_orchestrator = None
        self._initialize_rag()
        
    def _initialize_rag(self):
        """Initialize RAG system components"""
        try:
            # Try importing from replicated RAG system
            from pipeline import RAGPipeline
            from agents.orchestrator import RetrievalOrchestrator
            
            self.rag_pipeline = RAGPipeline()
            self.rag_orchestrator = RetrievalOrchestrator()
            logger.info("RAG system initialized successfully")
        except ImportError as e:
            try:
                # Fallback: try with rag_system prefix
                import sys
                import os
                rag_path = os.path.join(os.path.dirname(__file__), '..', 'rag_system')
                if rag_path not in sys.path:
                    sys.path.insert(0, rag_path)
                from pipeline import RAGPipeline
                from agents.orchestrator import RetrievalOrchestrator
                
                self.rag_pipeline = RAGPipeline()
                self.rag_orchestrator = RetrievalOrchestrator()
                logger.info("RAG system initialized successfully")
            except Exception as e2:
                logger.warning(f"RAG system initialization failed: {e2}. Will use fallback mode.")
                self.rag_pipeline = None
                self.rag_orchestrator = None
        except Exception as e:
            logger.warning(f"RAG system initialization failed: {e}. Will use fallback mode.")
            self.rag_pipeline = None
            self.rag_orchestrator = None
    
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """
        Query documents using RAG system
        
        Args:
            task: Must contain 'query' with question about documents
            context: Optional context about available documents
            
        Returns:
            AgentResult with document-based findings
        """
        query = task.get("query") or task.get("description", "")
        
        if not query:
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="No query provided for document analysis"
            )
        
        if not self.rag_orchestrator:
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error="RAG system not available"
            )
        
        try:
            # Query the RAG system
            rag_result = self.rag_orchestrator.process_query(query)
            
            # Extract relevant information
            findings = {
                "answer": rag_result.get("answer", ""),
                "sources": rag_result.get("sources", []),
                "retrieved_chunks": rag_result.get("retrieved_chunks", []),
                "metadata": rag_result.get("metadata", {})
            }
            
            return AgentResult(
                success=True,
                data={
                    "query": query,
                    "findings": findings,
                    "answer": rag_result.get("answer", ""),
                    "sources": self._format_sources(rag_result.get("sources", [])),
                    "confidence": rag_result.get("confidence", 0.7)
                },
                metadata={
                    "num_sources": len(rag_result.get("sources", [])),
                    "num_chunks": len(rag_result.get("retrieved_chunks", [])),
                    "rag_metadata": rag_result.get("metadata", {})
                }
            )
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            return AgentResult(
                success=False,
                data=None,
                metadata={},
                error=str(e)
            )
    
    def _format_sources(self, sources: List[Any]) -> List[Dict[str, str]]:
        """Format RAG sources into citation format"""
        formatted = []
        for i, source in enumerate(sources):
            if isinstance(source, dict):
                formatted.append({
                    "title": source.get("title", f"Document {i+1}"),
                    "type": source.get("type", "document"),
                    "chunk": source.get("content", "")[:200],
                    "metadata": source.get("metadata", {})
                })
            else:
                formatted.append({
                    "title": f"Document {i+1}",
                    "type": "document",
                    "chunk": str(source)[:200]
                })
        return formatted
    
    def check_documents_available(self) -> bool:
        """Check if documents are available in the RAG system"""
        if not self.rag_orchestrator:
            return False
        # In production, check Qdrant/Neo4j for document count
        return True

