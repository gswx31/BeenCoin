# app/middleware/rate_limit.py
"""
Rate limiting middleware
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Tuple
import time
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter implementation"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cleanup_interval = cleanup_interval
        
        # Storage for request counts
        self.minute_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.hour_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        # Cleanup task will be started when needed
        self._cleanup_task = None
    
    def _ensure_cleanup_task(self):
        """Ensure cleanup task is running"""
        if self._cleanup_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_old_entries())
            except RuntimeError:
                # No event loop running yet
                pass
    
    def _get_time_windows(self) -> Tuple[int, int]:
        """Get current minute and hour windows"""
        now = time.time()
        minute_window = int(now // 60)
        hour_window = int(now // 3600)
        return minute_window, hour_window
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if request is within rate limits
        
        Args:
            client_id: Client identifier (IP or user ID)
        
        Returns:
            bool: True if within limits, False otherwise
        """
        self._ensure_cleanup_task()  # Ensure cleanup is running
        
        minute_window, hour_window = self._get_time_windows()
        
        # Check minute limit
        minute_count = self.minute_counts[client_id][minute_window]
        if minute_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_id}: {minute_count}/min")
            return False
        
        # Check hour limit
        hour_count = self.hour_counts[client_id][hour_window]
        if hour_count >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded for {client_id}: {hour_count}/hour")
            return False
        
        # Increment counts
        self.minute_counts[client_id][minute_window] += 1
        self.hour_counts[client_id][hour_window] += 1
        
        return True
    
    def get_remaining_requests(self, client_id: str) -> Dict[str, int]:
        """Get remaining requests for client"""
        minute_window, hour_window = self._get_time_windows()
        
        minute_count = self.minute_counts[client_id][minute_window]
        hour_count = self.hour_counts[client_id][hour_window]
        
        return {
            "minute": max(0, self.requests_per_minute - minute_count),
            "hour": max(0, self.requests_per_hour - hour_count)
        }
    
    async def _cleanup_old_entries(self):
        """Clean up old entries periodically"""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            
            try:
                current_minute, current_hour = self._get_time_windows()
                
                # Clean minute counts (keep last 2 minutes)
                for client_id in list(self.minute_counts.keys()):
                    old_windows = [
                        w for w in self.minute_counts[client_id]
                        if w < current_minute - 1
                    ]
                    for window in old_windows:
                        del self.minute_counts[client_id][window]
                    
                    if not self.minute_counts[client_id]:
                        del self.minute_counts[client_id]
                
                # Clean hour counts (keep last 2 hours)
                for client_id in list(self.hour_counts.keys()):
                    old_windows = [
                        w for w in self.hour_counts[client_id]
                        if w < current_hour - 1
                    ]
                    for window in old_windows:
                        del self.hour_counts[client_id][window]
                    
                    if not self.hour_counts[client_id]:
                        del self.hour_counts[client_id]
                
                logger.debug(f"Cleaned up rate limit entries. Active clients: {len(self.minute_counts)}")
                
            except Exception as e:
                logger.error(f"Error in rate limit cleanup: {e}")


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
    
    Returns:
        Response or rate limit error
    """
    # Skip rate limiting for certain paths
    skip_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
    if request.url.path in skip_paths:
        return await call_next(request)
    
    # Get client identifier (IP address or user ID)
    client_id = request.client.host if request.client else "unknown"
    
    # Check rate limit
    if not rate_limiter.check_rate_limit(client_id):
        remaining = rate_limiter.get_remaining_requests(client_id)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please slow down.",
                "remaining": remaining
            },
            headers={
                "X-RateLimit-Remaining-Minute": str(remaining["minute"]),
                "X-RateLimit-Remaining-Hour": str(remaining["hour"]),
                "Retry-After": "60"
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.get_remaining_requests(client_id)
    response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute"])
    response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour"])
    
    return response