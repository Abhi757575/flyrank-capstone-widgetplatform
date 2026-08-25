import time
from collections import defaultdict
from typing import Dict, List, Tuple

class RateLimiter:
    def __init__(self, limit: int = 5, period_seconds: float = 60.0):
        """
        In-memory rate limiter using sliding window log.
        
        Args:
            limit: Maximum allowed requests within the period.
            period_seconds: Time window in seconds.
        """
        self.limit = limit
        self.period_seconds = period_seconds
        # Key: (client_ip, widget_id) -> Value: List of timestamps (floats)
        self.history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def is_rate_limited(self, ip: str, widget_id: str) -> bool:
        """
        Checks if the request should be rate limited.
        
        Returns:
            True if rate limited (429), False if allowed.
        """
        now = time.time()
        key = (ip, widget_id)
        
        # Filter out timestamps older than our sliding window period
        cutoff = now - self.period_seconds
        self.history[key] = [t for t in self.history[key] if t > cutoff]
        
        # Check if the number of requests exceeds the limit
        if len(self.history[key]) >= self.limit:
            return True
            
        # Log this successful request
        self.history[key].append(now)
        return False

# Create a global rate limiter instance
# Limit: 5 submissions per 60 seconds per IP/Widget
submission_rate_limiter = RateLimiter(limit=5, period_seconds=60.0)
