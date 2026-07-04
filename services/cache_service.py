import time
from typing import Any, Optional

class CacheService:
    """
    Simple in-memory cache service
    
    Why?
    - Store expensive query results temporarily
    - Return instantly without database query
    - Invalidate when data changes
    """
    
    def __init__(self):
        self.cache = {}
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """
        Store value in cache with expiry time
        
        ttl_seconds = how long to keep (default 1 hour)
        """
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Return None if:
        - Key doesn't exist
        - Key expired
        """
        if key not in self.cache:
            return None
        
        # Check if expired
        if time.time() > self.cache[key]["expires_at"]:
            del self.cache[key]  # Delete expired entry
            return None
        
        return self.cache[key]["value"]
    
    def invalidate(self, key: str):
        """Delete specific key from cache immediately"""
        if key in self.cache:
            del self.cache[key]
    
    def invalidate_pattern(self, pattern: str):
        """
        Delete all keys matching pattern
        
        Example: invalidate_pattern("stats_*") 
        Deletes: stats_sem2, stats_sem3, stats_sem4, etc
        """
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern.replace("*", ""))]
        for key in keys_to_delete:
            del self.cache[key]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()

# Global cache instance (used throughout app)
cache_service = CacheService()