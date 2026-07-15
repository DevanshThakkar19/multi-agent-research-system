"""Security and access control utilities for the RAG system."""
import re
from typing import Dict, Optional, List
from loguru import logger

from ..utils.config import settings


class SecurityManager:
    """Manages security, access control, and query validation."""
    
    def __init__(self):
        self.enabled = getattr(settings, 'enable_security', False)
        self.allowed_api_keys = self._load_api_keys()
        self.blocked_keywords = [
            # SQL injection attempts
            "'; DROP", "'; DELETE", "'; UPDATE", "'; INSERT",
            "UNION SELECT", "OR 1=1", "OR '1'='1",
            # Command injection attempts
            "; rm -rf", "; cat /etc/passwd", "| ls", "| cat",
            # Path traversal
            "../", "..\\", "/etc/passwd", "C:\\Windows",
            # Script injection
            "<script", "javascript:", "onerror=", "onclick="
        ]
        self.max_query_length = 1000  # Maximum query length
    
    def _load_api_keys(self) -> List[str]:
        """Load allowed API keys from environment or config."""
        api_key = getattr(settings, 'api_key', None)
        if api_key:
            return [api_key]
        return []
    
    def validate_query(self, query: str, api_key: Optional[str] = None) -> Dict[str, bool]:
        """
        Validate a query for security issues.
        
        Args:
            query: User query string
            api_key: Optional API key for authentication
        
        Returns:
            Dictionary with validation result and error message if invalid
        """
        if not self.enabled:
            return {"valid": True, "error": None}
        
        # Check API key if provided
        if api_key and self.allowed_api_keys:
            if api_key not in self.allowed_api_keys:
                logger.warning(f"Invalid API key provided")
                return {"valid": False, "error": "Invalid API key"}
        
        # Check query length
        if len(query) > self.max_query_length:
            logger.warning(f"Query too long: {len(query)} characters")
            return {"valid": False, "error": f"Query exceeds maximum length of {self.max_query_length} characters"}
        
        # Check for blocked keywords
        query_lower = query.lower()
        for keyword in self.blocked_keywords:
            if keyword.lower() in query_lower:
                logger.warning(f"Blocked keyword detected: {keyword}")
                return {"valid": False, "error": "Query contains potentially harmful content"}
        
        # Check for suspicious patterns
        # SQL injection patterns
        sql_patterns = [
            r"(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+",
            r"(\bOR\b|\bAND\b)\s+['\"]\d+['\"]\s*=\s*['\"]\d+['\"]",
            r"UNION\s+SELECT",
            r"';?\s*(DROP|DELETE|UPDATE|INSERT)",
            r";\s*(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER)\b"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Suspicious SQL pattern detected: {pattern}")
                return {"valid": False, "error": "Query contains suspicious patterns"}
        
        # Command injection patterns
        cmd_patterns = [
            r"[;&|]\s*(rm|cat|ls|pwd|whoami)",
            r"`[^`]+`",
            r"\$\([^)]+\)"
        ]
        for pattern in cmd_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Suspicious command pattern detected: {pattern}")
                return {"valid": False, "error": "Query contains suspicious command patterns"}
        
        return {"valid": True, "error": None}
    
    def sanitize_query(self, query: str) -> str:
        """
        Sanitize a query by removing potentially harmful content.
        
        Args:
            query: User query string
        
        Returns:
            Sanitized query string
        """
        # Remove null bytes
        query = query.replace('\x00', '')
        
        # Remove control characters (except newline and tab)
        query = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', query)
        
        # Limit length
        if len(query) > self.max_query_length:
            query = query[:self.max_query_length]
            logger.info(f"Query truncated to {self.max_query_length} characters")
        
        return query.strip()
    
    def check_access(self, resource: str, api_key: Optional[str] = None) -> bool:
        """
        Check if access is allowed to a resource.
        
        Args:
            resource: Resource identifier
            api_key: Optional API key
        
        Returns:
            True if access is allowed
        """
        if not self.enabled:
            return True
        
        if api_key and self.allowed_api_keys:
            return api_key in self.allowed_api_keys
        
        # Default: allow access if security is disabled or no API keys configured
        return True

