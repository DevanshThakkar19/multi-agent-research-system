"""Simple in-memory cache for embeddings and API responses."""
from typing import Dict, Optional
import hashlib
from loguru import logger


class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
    
    def _hash_key(self, key: str) -> str:
        """Hash key for storage."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[any]:
        """Get value from cache."""
        hashed_key = self._hash_key(key)
        if hashed_key in self.cache:
            return self.cache[hashed_key]["value"]
        return None
    
    def set(self, key: str, value: any):
        """Set value in cache."""
        hashed_key = self._hash_key(key)
        
        # Evict oldest if cache is full
        if len(self.cache) >= self.max_size and hashed_key not in self.cache:
            # Remove first item (oldest)
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[hashed_key] = {"value": value}
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        logger.info("Cache cleared")


# Global cache instance
_embedding_cache = SimpleCache(max_size=500)


def get_embedding_cache() -> SimpleCache:
    """Get global embedding cache."""
    return _embedding_cache




