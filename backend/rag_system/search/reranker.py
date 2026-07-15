"""Topic-based reranking for search results with cross-encoder support."""
from typing import List, Dict, Optional
from loguru import logger

# Try to import cross-encoder for better reranking
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")


class TopicReranker:
    """Rerank search results based on topic relevance with cross-encoder support."""
    
    def __init__(self, use_cross_encoder: bool = True,
                 cross_encoder_weight: float = 0.70,
                 original_weight: float = 0.20,
                 topic_weight: float = 0.10):
        self.topic_keywords = {
            "technology": ["technology", "software", "hardware", "computer", "system", "algorithm"],
            "business": ["business", "company", "revenue", "profit", "market", "customer"],
            "science": ["science", "research", "study", "experiment", "theory", "hypothesis"],
            "education": ["education", "learning", "teaching", "student", "course", "university"]
        }
        
        # Fine-tuned weights: 70% cross-encoder, 20% original, 10% topic
        # This gives more weight to cross-encoder for better precision
        self.cross_encoder_weight = cross_encoder_weight
        self.original_weight = original_weight
        self.topic_weight = topic_weight
        
        # Normalize weights to sum to 1.0
        total = cross_encoder_weight + original_weight + topic_weight
        if total > 0:
            self.cross_encoder_weight /= total
            self.original_weight /= total
            self.topic_weight /= total
        
        # Initialize cross-encoder for better precision
        self.cross_encoder = None
        self.use_cross_encoder = use_cross_encoder and CROSS_ENCODER_AVAILABLE
        
        if self.use_cross_encoder:
            try:
                # Use a lightweight cross-encoder model optimized for reranking
                self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                logger.info(f"Cross-encoder reranker initialized (weights: {self.cross_encoder_weight:.2f}/{self.original_weight:.2f}/{self.topic_weight:.2f})")
            except Exception as e:
                logger.warning(f"Failed to initialize cross-encoder: {e}. Falling back to topic-based reranking.")
                self.use_cross_encoder = False
    
    def rerank_by_topic(
        self,
        results: List[Dict],
        query: str,
        top_n: int = 10,
        modality_filter: Optional[str] = None,
        domain_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Rerank results based on topic relevance and cross-encoder scoring.
        
        Args:
            results: List of search results
            query: User query
            top_n: Number of top results to return
            modality_filter: Optional modality filter (text, image, audio, video)
            domain_filter: Optional domain filter (technology, business, science, education)
        
        Returns:
            Reranked results
        """
        if not results:
            return results
        
        # Apply metadata filters first
        filtered_results = self._apply_metadata_filters(results, modality_filter, domain_filter)
        
        # Detect query topic
        query_topic = self._detect_topic(query)
        
        # If cross-encoder is available, use it for better precision
        if self.use_cross_encoder and self.cross_encoder:
            scored_results = self._rerank_with_cross_encoder(filtered_results, query, query_topic)
        else:
            # Fallback to topic-based reranking
            scored_results = self._rerank_by_topic_only(filtered_results, query, query_topic)
        
        # Sort by final score
        reranked = sorted(scored_results, key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Reranked {len(filtered_results)} results by topic '{query_topic}' (cross-encoder: {self.use_cross_encoder}, filters: modality={modality_filter}, domain={domain_filter})")
        return reranked[:top_n]
    
    def _apply_metadata_filters(
        self,
        results: List[Dict],
        modality_filter: Optional[str],
        domain_filter: Optional[str]
    ) -> List[Dict]:
        """Apply metadata filters to results (soft filtering - only if we have enough results)."""
        if not modality_filter and not domain_filter:
            return results
        
        filtered = []
        for result in results:
            metadata = result.get("metadata", {})
            
            # Check modality filter
            if modality_filter:
                result_modality = metadata.get("modality", "").lower()
                if result_modality != modality_filter.lower():
                    continue
            
            # Check domain filter (soft - only filter if domain is explicitly set in metadata)
            if domain_filter:
                result_domain = metadata.get("domain", "").lower()
                # Only filter if domain is explicitly set and doesn't match
                # Don't filter if domain is "general" or empty (too aggressive)
                if result_domain and result_domain != "general" and result_domain != domain_filter.lower():
                    # Also check topic_relevance domain
                    topic_relevance = result.get("topic_relevance", {})
                    if isinstance(topic_relevance, dict):
                        topic_domain = topic_relevance.get("domain", "").lower()
                        if topic_domain and topic_domain != "general" and topic_domain != domain_filter.lower():
                            continue
                    else:
                        continue
            
            filtered.append(result)
        
        # Safety check: if filtering removed too many results, return original
        # Keep at least 50% of results to avoid over-filtering
        if len(filtered) < len(results) * 0.5:
            logger.warning(f"Metadata filtering too aggressive ({len(filtered)}/{len(results)} results), returning original results")
            return results
        
        if len(filtered) < len(results):
            logger.info(f"Filtered {len(results)} results to {len(filtered)} using metadata filters")
        
        return filtered if filtered else results  # Return original if all filtered out
    
    def _rerank_with_cross_encoder(
        self,
        results: List[Dict],
        query: str,
        query_topic: str
    ) -> List[Dict]:
        """Rerank using cross-encoder for better precision."""
        scored_results = []
        
        # Prepare query-document pairs for cross-encoder
        pairs = []
        for result in results:
            content = result.get("content", "")
            # Truncate content to avoid token limits (cross-encoder has 512 token limit)
            if len(content) > 500:
                content = content[:500] + "..."
            pairs.append([query, content])
        
        # Get cross-encoder scores (batch processing)
        try:
            cross_scores = self.cross_encoder.predict(pairs, show_progress_bar=False)
        except Exception as e:
            logger.warning(f"Cross-encoder prediction failed: {e}. Falling back to topic-based.")
            return self._rerank_by_topic_only(results, query, query_topic)
        
        # Combine cross-encoder scores with original scores and topic relevance
        # First, normalize all cross-encoder scores to 0-1 range using min-max normalization
        if len(cross_scores) > 0:
            min_score = min(cross_scores)
            max_score = max(cross_scores)
            score_range = max_score - min_score if max_score != min_score else 1.0
        else:
            min_score = 0.0
            score_range = 1.0
        
        for i, result in enumerate(results):
            original_score = result.get("score", 0.0)
            cross_score = float(cross_scores[i]) if i < len(cross_scores) else 0.0
            
            # Normalize cross-encoder score using min-max normalization
            normalized_cross_score = (cross_score - min_score) / score_range
            normalized_cross_score = max(0.0, min(1.0, normalized_cross_score))  # Clamp to [0, 1]
            
            # Calculate topic boost
            content = result.get("content", "").lower()
            topic_boost = self._calculate_topic_relevance(content, query_topic)
            
            # Combine scores using fine-tuned weights (70/20/10)
            final_score = (
                normalized_cross_score * self.cross_encoder_weight +
                original_score * self.original_weight +
                topic_boost * self.topic_weight
            )
            
            # Add domain tag to metadata
            metadata = result.get("metadata", {})
            metadata["domain"] = query_topic
            metadata["topic_relevance_score"] = topic_boost
            metadata["cross_encoder_score"] = normalized_cross_score
            
            scored_results.append({
                **result,
                "score": final_score,
                "topic_relevance": {
                    "domain": query_topic,
                    "score": topic_boost
                },
                "metadata": metadata
            })
        
        return scored_results
    
    def _rerank_by_topic_only(
        self,
        results: List[Dict],
        query: str,
        query_topic: str
    ) -> List[Dict]:
        """Fallback topic-based reranking without cross-encoder."""
        scored_results = []
        for result in results:
            content = result.get("content", "").lower()
            score = result.get("score", 0.0)
            
            # Boost score if content matches query topic
            topic_boost = self._calculate_topic_relevance(content, query_topic)
            boosted_score = score * (1 + topic_boost * 0.2)  # 20% boost max
            
            # Add domain tag to metadata
            metadata = result.get("metadata", {})
            metadata["domain"] = query_topic
            metadata["topic_relevance_score"] = topic_boost
            
            scored_results.append({
                **result,
                "score": boosted_score,
                "topic_relevance": {
                    "domain": query_topic,
                    "score": topic_boost
                },
                "metadata": metadata
            })
        
        return scored_results
    
    def _detect_topic(self, query: str) -> str:
        """Detect the topic of a query."""
        query_lower = query.lower()
        
        topic_scores = {}
        for topic, keywords in self.topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            return max(topic_scores, key=topic_scores.get)
        return "general"
    
    def _calculate_topic_relevance(self, content: str, topic: str) -> float:
        """Calculate how relevant content is to a topic."""
        if topic == "general":
            return 0.0
        
        keywords = self.topic_keywords.get(topic, [])
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in content)
        # Normalize to 0-1 range
        relevance = min(matches / len(keywords), 1.0)
        return relevance
