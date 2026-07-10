import redis
import json
import time
from typing import Any, Optional

class RedisCacheService:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        json_value = json.dumps(value)
        self.redis_client.setex(key, ttl_seconds, json_value)
    
    def get(self, key: str) -> Optional[Any]:
        value = self.redis_client.get(key)
        if value is None:
            return None
        return json.loads(value)
    
    def invalidate(self, key: str):
        self.redis_client.delete(key)
    
    def invalidate_pattern(self, pattern: str):
        keys = self.redis_client.keys(pattern + "*")
        if keys:
            self.redis_client.delete(*keys)
    
    def clear(self):
        self.redis_client.flushdb()

redis_cache_service = RedisCacheService()