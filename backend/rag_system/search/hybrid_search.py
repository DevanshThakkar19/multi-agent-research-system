"""Hybrid search combining graph, keyword, and vector retrieval."""
from typing import List, Dict, Optional
from loguru import logger

from ..graph.neo4j_client import Neo4jClient
from ..vector.qdrant_client import QdrantClient
from ..evaluation.metrics import QueryType
from .query_rewriter import QueryRewriter
from .reranker import TopicReranker


class HybridSearch:
    """Hybrid search combining multiple retrieval methods."""
    
    def __init__(self):
        self.neo4j_client = Neo4jClient()
        self.qdrant_client = QdrantClient()
        self.query_rewriter = QueryRewriter()
        self.reranker = TopicReranker()
    
    def search(
        self,
        query: str,
        query_type: Optional[QueryType] = None,
        top_k: int = 10,
        use_graph: bool = True,
        use_vector: bool = True,
        use_keyword: bool = True,
        modality_filter: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> Dict:
        """
        Perform hybrid search.
        
        Args:
            query: User query
            query_type: Type of query
            top_k: Number of results to return
            use_graph: Whether to use graph traversal
            use_vector: Whether to use vector search
            use_keyword: Whether to use keyword filtering
        
        Returns:
            Dictionary with combined search results
        """
        # Rewrite query
        query_info = self.query_rewriter.rewrite_query(query, query_type)
        rewritten_query = query_info["rewritten_query"]
        keywords = query_info["keywords"]
        
        results = {
            "query": query,
            "rewritten_query": rewritten_query,
            "query_type": query_info["query_type"],
            "results": [],
            "sources": {
                "graph": [],
                "vector": [],
                "keyword": []
            }
        }
        
        # Graph traversal search
        if use_graph:
            graph_results = self._graph_search(keywords, query_type)
            results["sources"]["graph"] = graph_results
        
        # Vector semantic search
        if use_vector:
            vector_results = self.qdrant_client.search(
                rewritten_query,
                top_k=top_k,
                score_threshold=0.1  # Lower threshold to include more results
            )
            results["sources"]["vector"] = vector_results
        
        # Keyword filtering
        if use_keyword:
            keyword_results = self._keyword_search(keywords)
            results["sources"]["keyword"] = keyword_results
        
        # Combine and rank results
        # Retrieve 3x more candidates for better reranking with cross-encoder
        combined_results = self._combine_and_rank(
            results["sources"],
            top_k=top_k * 3  # Get 3x more results for cross-encoder reranking
        )
        
        # Apply improved reranking (with cross-encoder if available)
        results["results"] = self.reranker.rerank_by_topic(
            combined_results,
            query=query,
            top_n=top_k,  # Return only top_k after reranking
            modality_filter=modality_filter,
            domain_filter=domain_filter
        )
        
        return results
    
    def _graph_search(self, keywords: List[str], query_type: Optional[QueryType]) -> List[Dict]:
        """Search using graph traversal."""
        graph_results = []
        
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            try:
                # Query graph for entities matching keyword
                entities = self.neo4j_client.query_graph(
                    entity_name=keyword,
                    limit=5
                )
                
                for entity_data in entities:
                    entity = entity_data["entity"]
                    relationships = entity_data["relationships"]
                    
                    # Get related entities through traversal
                    if entity.get("id"):
                        traversal = self.neo4j_client.traverse_from_entity(
                            entity["id"],
                            max_depth=2
                        )
                        
                        graph_results.append({
                            "type": "graph",
                            "entity": entity,
                            "relationships": relationships,
                            "traversal": traversal,
                            "score": 0.8  # Graph results get high score
                        })
            except Exception as e:
                logger.warning(f"Graph search failed for keyword {keyword}: {e}")
        
        return graph_results
    
    def _keyword_search(self, keywords: List[str]) -> List[Dict]:
        """Search using keyword filtering in vector database."""
        keyword_results = []
        
        # Search vector DB with keyword filters
        for keyword in keywords[:5]:
            if not keyword:
                continue
            try:
                # Use simple vector search for keywords (Qdrant doesn't support $contains in filters easily)
                # We'll search by embedding similarity which works well for keywords
                results = self.qdrant_client.search(
                    keyword,
                    top_k=5,
                    filters=None  # Keyword search via semantic similarity
                )
                keyword_results.extend(results)
            except Exception as e:
                logger.warning(f"Keyword search failed: {e}")
        
        return keyword_results
    
    def _combine_and_rank(
        self,
        sources: Dict,
        top_k: int = 10
    ) -> List[Dict]:
        """Combine results from different sources and rank them."""
        all_results = []
        
        # Add graph results
        for graph_result in sources.get("graph", []):
            all_results.append({
                "content": str(graph_result.get("entity", {})),
                "source": "graph",
                "score": graph_result.get("score", 0.8),
                "metadata": graph_result
            })
        
        # Add vector results
        for vector_result in sources.get("vector", []):
            all_results.append({
                "content": vector_result.get("text", ""),
                "source": "vector",
                "score": vector_result.get("score", 0.0),
                "metadata": vector_result.get("metadata", {})
            })
        
        # Add keyword results (with lower weight)
        for keyword_result in sources.get("keyword", []):
            all_results.append({
                "content": keyword_result.get("text", ""),
                "source": "keyword",
                "score": keyword_result.get("score", 0.0) * 0.7,  # Lower weight
                "metadata": keyword_result.get("metadata", {})
            })
        
        # Deduplicate and rank
        seen = set()
        unique_results = []
        
        # Sort by score, but preserve order for audio chunks from same file
        sorted_results = sorted(all_results, key=lambda x: (
            -x["score"],  # Primary: higher score first
            x["metadata"].get("chunk_index", 999) if x["metadata"].get("modality") == "audio" else 999  # Secondary: audio chunks in order
        ))
        
        for result in sorted_results:
            content_hash = hash(result["content"][:100])  # Hash first 100 chars
            if content_hash not in seen:
                seen.add(content_hash)
                unique_results.append(result)
                if len(unique_results) >= top_k:
                    break
        
        return unique_results

