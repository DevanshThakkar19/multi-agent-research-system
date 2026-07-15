"""Agent-based retrieval orchestration."""
import time
from typing import Dict, Optional, List
from loguru import logger

from ..search.hybrid_search import HybridSearch
from ..evaluation.metrics import QueryType
from ..generation.answer_generator import AnswerGenerator
from ..utils.security import SecurityManager


class RetrievalOrchestrator:
    """Orchestrates retrieval and answer generation."""
    
    def __init__(self):
        self.hybrid_search = HybridSearch()
        self.answer_generator = AnswerGenerator()
        self.security_manager = SecurityManager()
    
    def process_query(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        max_context_length: int = 4000
    ) -> Dict:
        """
        Process a user query end-to-end.
        
        Args:
            query: User query
            query_type: Type of query (if known)
            max_context_length: Maximum context length for answer generation
        
        Returns:
            Dictionary with answer and metadata
        """
        start_time = time.time()  # Start timing for full query latency
        try:
            # Security: Validate and sanitize query
            validation = self.security_manager.validate_query(query)
            if not validation["valid"]:
                logger.warning(f"Query validation failed: {validation['error']}")
                return {
                    "query": query,
                    "answer": f"I cannot process this query: {validation['error']}. Please rephrase your question.",
                    "sources": [],
                    "error": validation["error"]
                }
            
            # Sanitize query
            query = self.security_manager.sanitize_query(query)
            
            # Check if this is an audio-related query - need more results to get all segments
            audio_keywords = ["audio", "said", "transcription", "transcribe", "spoken", "speech", "what was"]
            is_audio_query = any(keyword in query.lower() for keyword in audio_keywords)
            top_k = 20 if is_audio_query else 10  # Get more results for audio to ensure all segments
            # Increase context length for audio to accommodate full transcriptions
            effective_max_length = max_context_length * 2 if is_audio_query else max_context_length
            
            # Detect modality and domain from query for filtering (very conservative - only for explicit queries)
            # Disable filtering for now to avoid over-filtering - can be re-enabled if needed
            modality_filter = None  # self._detect_modality_from_query(query)  # Disabled to prevent over-filtering
            domain_filter = None  # self._detect_domain_from_query(query)  # Disabled to prevent over-filtering
            
            # Perform hybrid search (without metadata filters for now)
            search_results = self.hybrid_search.search(
                query=query,
                query_type=query_type,
                top_k=top_k,
                modality_filter=modality_filter,
                domain_filter=domain_filter
            )
            
            # Extract context from search results
            context = self._extract_context(
                search_results["results"],
                max_length=effective_max_length,
                query=query
            )
            
            # Generate answer
            answer = self.answer_generator.generate_answer(
                query=query,
                context=context,
                query_type=search_results["query_type"]
            )
            
            # Calculate total latency
            total_latency_ms = (time.time() - start_time) * 1000
            
            return {
                "query": query,
                "answer": answer["answer"],
                "sources": answer.get("sources", []),
                "search_results": search_results,
                "metadata": {
                    "query_type": search_results["query_type"].value,
                    "context_length": len(context),
                    "num_sources": len(search_results["results"]),
                    "latency_ms": total_latency_ms  # Full query latency
                }
            }
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return {
                "query": query,
                "answer": "I apologize, but I encountered an error processing your query. Please try again.",
                "sources": [],
                "error": str(e)
            }
    
    def _extract_context(self, results: List[Dict], max_length: int, query: str = "") -> str:
        """Extract and format context from search results."""
        if not results:
            logger.warning("No results provided for context extraction")
            return ""
        
        # Check if this is an audio-related query
        audio_keywords = ["audio", "said", "transcription", "transcribe", "transcript", "spoken", "speech", "what was", "what does", "video say", "video said", "video talk", "give transcript", "show transcript", "talk", "talks"]
        is_audio_query = any(keyword in query.lower() for keyword in audio_keywords)
        
        # Separate audio chunks from other results
        audio_chunks = []
        other_results = []
        audio_file_ids = set()
        
        for result in results:
            metadata = result.get("metadata", {})
            modality = metadata.get("modality", "")
            # Treat video chunks with transcription as audio chunks for audio queries
            if modality == "audio" or (modality == "video" and is_audio_query):
                audio_chunks.append(result)
                file_id = metadata.get("file_id", "")
                if file_id:
                    audio_file_ids.add(file_id)
            else:
                other_results.append(result)
        
        # Sort audio chunks by chunk_index to preserve order
        audio_chunks.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 999))
        
        # For audio queries, try to get ALL chunks from the same file(s)
        # by searching for missing chunk indices
        if is_audio_query and audio_file_ids:
            # Find the max chunk_index we have
            max_chunk_idx = max(
                (chunk.get("metadata", {}).get("chunk_index", -1) for chunk in audio_chunks),
                default=-1
            )
            
            # If we have chunks 0, 1, 2 but not 3, try to find chunk 3
            # This ensures we get the complete transcription
            for file_id in audio_file_ids:
                for idx in range(max_chunk_idx + 1):
                    # Check if we already have this chunk
                    has_chunk = any(
                        chunk.get("metadata", {}).get("chunk_index") == idx and
                        chunk.get("metadata", {}).get("file_id") == file_id
                        for chunk in audio_chunks
                    )
                    if not has_chunk:
                        # Try to find it in the original results (might have lower score)
                        for result in results:
                            metadata = result.get("metadata", {})
                            modality = metadata.get("modality", "")
                            # Include both audio and video chunks for audio queries
                            if ((modality == "audio" or (modality == "video" and is_audio_query)) and
                                metadata.get("file_id") == file_id and
                                metadata.get("chunk_index") == idx):
                                if result not in audio_chunks:
                                    audio_chunks.append(result)
                                    break
        
        # Re-sort after adding missing chunks
        audio_chunks.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 999))
        
        # Combine: audio chunks first (in order), then other results
        ordered_results = audio_chunks + other_results
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(ordered_results, 1):
            content = result.get("content", "")
            source = result.get("source", "unknown")
            metadata = result.get("metadata", {})
            modality = metadata.get("modality", "unknown")
            
            # Skip empty content
            if not content or not isinstance(content, str):
                logger.warning(f"Skipping result with invalid content: {type(content)}")
                continue
            
            # Calculate remaining space
            remaining_length = max_length - current_length
            
            # If no space left, break
            if remaining_length <= 0:
                break
            
            # Truncate content if needed
            if len(content) > remaining_length:
                content = content[:remaining_length - 50] + "..."  # Leave room for "..."
            
            # Format context with modality info for better LLM understanding
            if modality == "audio":
                chunk_idx = metadata.get("chunk_index", "")
                context_parts.append(f"[Source: {source} | Audio Transcription | Segment {chunk_idx}]\n{content}\n")
            elif modality == "video":
                # For audio queries, video chunks with transcription should be treated as audio
                if is_audio_query:
                    chunk_idx = metadata.get("chunk_index", "")
                    context_parts.append(f"[Source: {source} | Video Content | Audio Transcription | Segment {chunk_idx}]\n{content}\n")
                elif "transcription" in content.lower() or len(content) > 50:
                    # This is likely transcribed audio from video
                    context_parts.append(f"[Source: {source} | Video Content | Audio Transcription]\n{content}\n")
                else:
                    context_parts.append(f"[Source: {source} | Video Content]\n{content}\n")
            elif modality == "image":
                context_parts.append(f"[Source: {source} | Image Content]\n{content}\n")
            else:
                context_parts.append(f"[Source: {source}]\n{content}\n")
            
            current_length += len(content)
        
        context = "\n".join(context_parts)
        logger.info(f"Extracted context: {len(context)} characters from {len(results)} results ({len(audio_chunks)} audio chunks)")
        return context
    
    def _detect_modality_from_query(self, query: str) -> Optional[str]:
        """Detect modality from query keywords (soft filtering - only for very specific queries)."""
        if not query or len(query.strip()) == 0:
            return None
            
        query_lower = query.lower()
        
        # Only filter if query is very specific about modality
        # Image keywords (must be explicit)
        if any(kw in query_lower for kw in ["image", "picture", "photo", "diagram", "chart", "visual", "png", "jpg", "jpeg"]):
            return "image"
        
        # Video keywords (must be explicit)
        if any(kw in query_lower for kw in ["video", "movie", "clip", "frame", "scene", "mp4", "avi"]):
            return "video"
        
        # Audio keywords (must be explicit)
        if any(kw in query_lower for kw in ["audio", "sound", "transcription", "transcribe", "spoken", "speech", "mp3", "wav"]):
            return "audio"
        
        # Text keywords (only if very explicit, not just "file" or "content")
        if any(kw in query_lower for kw in ["text document", "txt file", "pdf document"]):
            return "text"
        
        return None  # No specific modality detected - don't filter
    
    def _detect_domain_from_query(self, query: str) -> Optional[str]:
        """Detect domain from query keywords (soft filtering - only for very specific queries)."""
        if not query or len(query.strip()) == 0:
            return None
            
        query_lower = query.lower()
        
        # Only filter if query is very specific about domain
        # Technology domain (must be explicit)
        if any(kw in query_lower for kw in ["technology", "software", "hardware", "computer", "algorithm", "code", "programming", "html", "api"]):
            return "technology"
        
        # Business domain (must be explicit)
        if any(kw in query_lower for kw in ["business", "company", "revenue", "profit", "market", "investment", "buffett", "financial"]):
            return "business"
        
        # Science domain (must be explicit)
        if any(kw in query_lower for kw in ["science", "research", "study", "experiment", "theory", "hypothesis"]):
            return "science"
        
        # Education domain (must be explicit)
        if any(kw in query_lower for kw in ["education", "learning", "teaching", "student", "course", "university", "lesson", "tutorial"]):
            return "education"
        
        return None  # No specific domain detected - don't filter

