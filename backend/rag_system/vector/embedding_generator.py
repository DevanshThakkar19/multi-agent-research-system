"""Generate embeddings for content."""
from typing import List, Union
from openai import OpenAI
from loguru import logger

from ..utils.config import settings
from ..utils.cache import get_embedding_cache


class EmbeddingGenerator:
    """Generate embeddings using OpenAI with caching."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.cache = get_embedding_cache()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text (with caching)."""
        # Check cache first
        cache_key = f"{self.model}:{text}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return cached
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            # Cache the result
            self.cache.set(cache_key, embedding)
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts (with caching and batching)."""
        # Quick path: if no texts, return empty
        if not texts:
            return []
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache for each text (optimized)
        for i, text in enumerate(texts):
            cache_key = f"{self.model}:{text}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                embeddings.append((i, cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts in batches
        if uncached_texts:
            if len(embeddings) > 0:
                logger.debug(f"Cache hit: {len(embeddings)}/{len(texts)}, generating {len(uncached_texts)} new embeddings")
            for batch_start in range(0, len(uncached_texts), batch_size):
                batch_texts = uncached_texts[batch_start:batch_start + batch_size]
                batch_indices = uncached_indices[batch_start:batch_start + batch_size]
                
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch_texts
                    )
                    # Cache and store results
                    for batch_idx, (idx, item) in enumerate(zip(batch_indices, response.data)):
                        embedding = item.embedding
                        cache_key = f"{self.model}:{batch_texts[batch_idx]}"
                        self.cache.set(cache_key, embedding)
                        embeddings.append((idx, embedding))
                except Exception as e:
                    logger.error(f"Batch embedding generation failed: {e}")
                    raise
        
        # Sort by original index and return just embeddings
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]

