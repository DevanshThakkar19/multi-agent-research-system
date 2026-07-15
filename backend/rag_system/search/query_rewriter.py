"""Query rewriting and enhancement."""
from typing import Dict, Optional, List
from openai import OpenAI
from loguru import logger

from ..utils.config import settings
from ..evaluation.metrics import QueryType


class QueryRewriter:
    """Rewrite and enhance queries for better retrieval."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    def rewrite_query(self, query: str, query_type: Optional[QueryType] = None) -> Dict:
        """
        Rewrite query to improve retrieval.
        
        Args:
            query: Original user query
            query_type: Type of query (if known)
        
        Returns:
            Dictionary with rewritten query and keywords
        """
        try:
            # Determine query type if not provided
            if query_type is None:
                query_type = self._classify_query_type(query)
            
            # Rewrite based on query type
            rewritten_query = self._rewrite_by_type(query, query_type)
            
            # Extract keywords
            keywords = self._extract_keywords(query)
            
            return {
                "original_query": query,
                "rewritten_query": rewritten_query,
                "query_type": query_type,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            return {
                "original_query": query,
                "rewritten_query": query,
                "query_type": QueryType.LOOKUP,
                "keywords": query.split()
            }
    
    def _classify_query_type(self, query: str) -> QueryType:
        """Classify query type."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["summarize", "summary", "overview"]):
            return QueryType.SUMMARIZATION
        elif any(word in query_lower for word in ["how", "why", "what is the relationship", "related"]):
            return QueryType.SEMANTIC_LINKAGES
        elif any(word in query_lower for word in ["if", "calculate", "reason", "infer"]):
            return QueryType.REASONING
        else:
            return QueryType.LOOKUP
    
    def _rewrite_by_type(self, query: str, query_type: QueryType) -> str:
        """Rewrite query based on type."""
        prompt = f"""Rewrite the following query to improve information retrieval. 
Query type: {query_type.value}
Original query: {query}

Provide a rewritten version that:
1. Expands key terms and concepts
2. Includes synonyms and related terms
3. Maintains the original intent
4. Is optimized for semantic search

Rewritten query:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Query rewriting failed, using original: {e}")
            return query
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query."""
        # Simple keyword extraction - could be enhanced with NLP
        import re
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return keywords[:10]  # Limit to top 10 keywords

