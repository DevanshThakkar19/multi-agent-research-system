"""Qdrant client for vector database operations."""
from typing import List, Dict, Optional
import uuid
from qdrant_client import QdrantClient as Qdrant
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from loguru import logger

from ..utils.config import settings
from .embedding_generator import EmbeddingGenerator


class QdrantClient:
    """Client for Qdrant vector database operations."""
    
    def __init__(self):
        self.client = Qdrant(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        self.collection_name = settings.qdrant_collection_name
        self.embedding_generator = EmbeddingGenerator()
        self._initialize_collection()
    
    def _initialize_collection(self):
        """Initialize Qdrant collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            # Get embedding dimension from a test embedding
            try:
                test_embedding = self.embedding_generator.generate_embedding("test")
                embedding_dim = len(test_embedding)
            except Exception as e:
                logger.warning(f"Could not generate test embedding, using default dimension: {e}")
                embedding_dim = 1536  # Default for text-embedding-3-small
            
            if self.collection_name not in collection_names:
                # Create new collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,  # Dynamic dimension based on model
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name} with dimension {embedding_dim}")
            else:
                # Check if existing collection has correct dimension
                collection_info = self.client.get_collection(self.collection_name)
                existing_dim = collection_info.config.params.vectors.size
                
                if existing_dim != embedding_dim:
                    logger.warning(
                        f"Collection dimension mismatch: existing={existing_dim}, expected={embedding_dim}. "
                        f"Recreating collection..."
                    )
                    # Delete and recreate with correct dimension
                    self.client.delete_collection(self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=embedding_dim,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Recreated collection: {self.collection_name} with dimension {embedding_dim}")
                else:
                    logger.info(f"Collection {self.collection_name} already exists with correct dimension {embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def add_documents(
        self,
        texts: List[str],
        metadata_list: List[Dict],
        ids: Optional[List[str]] = None,
        batch_size: int = 100
    ):
        """Add documents to the vector database (optimized with batching)."""
        if not texts or not metadata_list:
            logger.warning("No texts or metadata provided")
            return
        
        if len(texts) != len(metadata_list):
            raise ValueError("Texts and metadata lists must have the same length")
        
        # Process in batches for better performance
        total = len(texts)
        if total > batch_size:
            logger.info(f"Indexing {total} documents in batches of {batch_size}")
        else:
            logger.debug(f"Indexing {total} documents")
        
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_texts = texts[batch_start:batch_end]
            batch_metadata = metadata_list[batch_start:batch_end]
            batch_ids = ids[batch_start:batch_end] if ids else None
            
            # Generate embeddings for this batch
            batch_embeddings = self.embedding_generator.generate_embeddings(batch_texts)
            
            # Create points for this batch
            points = []
            for i, (text, metadata, embedding) in enumerate(zip(batch_texts, batch_metadata, batch_embeddings)):
                # Qdrant accepts string UUIDs or unsigned integers
                # Convert string IDs to UUID strings for consistency
                if batch_ids and i < len(batch_ids):
                    point_id_str = batch_ids[i]
                    # Try to convert to UUID string if it's a string
                    try:
                        # If it's already a valid UUID format, use it
                        if isinstance(point_id_str, str) and len(point_id_str) == 36:
                            point_id = str(uuid.UUID(point_id_str))
                        else:
                            # Generate UUID from string hash for consistency
                            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id_str))
                    except (ValueError, AttributeError):
                        # Fallback: generate UUID from string
                        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(point_id_str)))
                else:
                    # Generate new UUID
                    point_id = str(uuid.uuid4())
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "text": text,
                            **metadata
                        }
                    )
                )
            
            # Upload batch to Qdrant
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.debug(f"Uploaded batch {batch_start//batch_size + 1}: {len(points)} documents")
            except Exception as e:
                logger.error(f"Failed to add documents to Qdrant: {e}")
                raise
        
        logger.info(f"Successfully indexed {total} documents in Qdrant")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None,
        score_threshold: float = 0.0
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional filters (e.g., {"modality": "text"})
            score_threshold: Minimum similarity score
        
        Returns:
            List of search results with scores
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Build filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                # Handle different filter types
                if isinstance(value, dict):
                    # Support for operators like $contains (text matching)
                    if "$contains" in value:
                        try:
                            from qdrant_client.models import MatchText
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    match=MatchText(text=value["$contains"])
                                )
                            )
                        except ImportError:
                            # Fallback to regular match if MatchText not available
                            logger.warning("MatchText not available, using MatchValue")
                            conditions.append(
                                FieldCondition(
                                    key=key,
                                    match=MatchValue(value=value.get("$contains", value))
                                )
                            )
                    else:
                        conditions.append(
                            FieldCondition(
                                key=key,
                                match=MatchValue(value=value)
                            )
                        )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            if conditions:
                query_filter = Filter(must=conditions)
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            score_threshold=score_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "metadata": {k: v for k, v in result.payload.items() if k != "text"}
            })
        
        return formatted_results
    
    def delete_by_metadata(self, filters: Dict):
        """Delete documents matching metadata filters."""
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        if conditions:
            query_filter = Filter(must=conditions)
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=query_filter
            )
            logger.info(f"Deleted documents matching filters: {filters}")

