import time
import logging
from flask import request, jsonify
from functools import wraps
import threading
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter implementation using either Redis or in-memory storage.
    
    Supports:
    - IP-based rate limiting
    - Custom request limits and time windows
    - Redis backend (preferred) for distributed deployments
    - In-memory fallback for development or when Redis is unavailable
    """
    
    def __init__(self, app=None, redis_url=None, default_limits=None):
        """
        Initialize the rate limiter.
        
        Args:
            app (Flask): Flask application instance
            redis_url (str): Redis connection URL for distributed rate limiting
            default_limits (dict): Default rate limits, format:
                {
                    "requests": 100,       # Number of requests allowed
                    "period": 3600,        # Time window in seconds
                    "by_endpoint": False   # Whether to limit per endpoint or globally
                }
        """
        self.default_limits = default_limits or {
            "requests": 100,
            "period": 3600,  # 1 hour in seconds
            "by_endpoint": False
        }
        
        # Redis connection
        self.redis = None
        self.redis_url = redis_url
        self.use_redis = False
        
        # In-memory storage as fallback
        self.in_memory_storage = {}
        self.storage_lock = threading.Lock()
        
        # Initialize with app if provided
        if app is not None:
            self.init_app(app)
            
    def init_app(self, app):
        """
        Initialize the rate limiter with a Flask app.
        
        Args:
            app (Flask): Flask application instance
        """
        # Try to connect to Redis if URL is provided
        if self.redis_url:
            try:
                self.redis = redis.from_url(self.redis_url)
                self.redis.ping()
                self.use_redis = True
                logger.info("Connected to Redis for distributed rate limiting")
            except (redis.exceptions.ConnectionError, RedisError) as e:
                logger.warning(f"Could not connect to Redis, falling back to in-memory storage: {e}")
                self.use_redis = False
        
        # Set default limits from app config if available
        if app.config.get('RATE_LIMIT_REQUESTS'):
            self.default_limits['requests'] = app.config.get('RATE_LIMIT_REQUESTS')
            
        if app.config.get('RATE_LIMIT_PERIOD'):
            self.default_limits['period'] = app.config.get('RATE_LIMIT_PERIOD')
            
        if app.config.get('RATE_LIMIT_BY_ENDPOINT') is not None:
            self.default_limits['by_endpoint'] = app.config.get('RATE_LIMIT_BY_ENDPOINT')
        
        # Clean up expired entries periodically
        if not self.use_redis:
            @app.before_request
            def cleanup_expired_entries():
                self._cleanup_expired()
    
    def _get_rate_limit_key(self, endpoint=None):
        """
        Get a unique key for the current request based on client IP and optionally endpoint.
        
        Args:
            endpoint (str, optional): The endpoint name to include in the key
            
        Returns:
            str: Rate limit key
        """
        # Get client IP address
        ip = request.remote_addr
        
        # Use X-Forwarded-For if behind a proxy
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        # Create key based on IP and optionally endpoint
        if endpoint and self.default_limits['by_endpoint']:
            return f"ratelimit:{ip}:{endpoint}"
        else:
            return f"ratelimit:{ip}"
    
    def _get_current_usage(self, key):
        """
        Get current rate limit usage for a key.
        
        Args:
            key (str): Rate limit key
            
        Returns:
            tuple: (count, reset_time) - Number of requests and reset timestamp
        """
        if self.use_redis:
            try:
                pipe = self.redis.pipeline()
                pipe.get(f"{key}:count")
                pipe.get(f"{key}:reset")
                result = pipe.execute()
                
                count = int(result[0]) if result[0] else 0
                reset_time = int(result[1]) if result[1] else int(time.time()) + self.default_limits['period']
                
                return count, reset_time
            except RedisError as e:
                logger.error(f"Redis error in _get_current_usage: {e}")
                # Fall back to in-memory if Redis fails
                self.use_redis = False
        
        # In-memory implementation
        with self.storage_lock:
            if key not in self.in_memory_storage:
                reset_time = int(time.time()) + self.default_limits['period']
                self.in_memory_storage[key] = {
                    'count': 0,
                    'reset': reset_time
                }
            
            # Reset if period has expired
            if self.in_memory_storage[key]['reset'] <= int(time.time()):
                reset_time = int(time.time()) + self.default_limits['period']
                self.in_memory_storage[key] = {
                    'count': 0,
                    'reset': reset_time
                }
                
            return self.in_memory_storage[key]['count'], self.in_memory_storage[key]['reset']
    
    def _increment_usage(self, key):
        """
        Increment the usage count for a key.
        
        Args:
            key (str): Rate limit key
            
        Returns:
            tuple: (count, reset_time) - Updated count and reset timestamp
        """
        if self.use_redis:
            try:
                pipe = self.redis.pipeline()
                current_time = int(time.time())
                
                # Check if we need to reset the counter
                pipe.get(f"{key}:reset")
                result = pipe.execute()
                
                reset_time = int(result[0]) if result[0] else current_time + self.default_limits['period']
                
                # Reset counter if expired
                if reset_time <= current_time:
                    reset_time = current_time + self.default_limits['period']
                    pipe.set(f"{key}:count", 1)
                    pipe.set(f"{key}:reset", reset_time)
                    pipe.execute()
                    return 1, reset_time
                
                # Increment counter
                pipe.incr(f"{key}:count")
                pipe.expire(f"{key}:count", self.default_limits['period'])
                pipe.expire(f"{key}:reset", self.default_limits['period'])
                result = pipe.execute()
                
                return int(result[0]), reset_time
            except RedisError as e:
                logger.error(f"Redis error in _increment_usage: {e}")
                # Fall back to in-memory if Redis fails
                self.use_redis = False
        
        # In-memory implementation
        with self.storage_lock:
            count, reset_time = self._get_current_usage(key)
            self.in_memory_storage[key]['count'] += 1
            return self.in_memory_storage[key]['count'], reset_time
    
    def _cleanup_expired(self):
        """Clean up expired rate limit entries from in-memory storage."""
        if not self.use_redis:
            current_time = int(time.time())
            with self.storage_lock:
                # Find expired keys
                expired_keys = [
                    key for key, data in self.in_memory_storage.items()
                    if data['reset'] <= current_time
                ]
                
                # Remove expired keys
                for key in expired_keys:
                    del self.in_memory_storage[key]
    
    def limit(self, requests=None, period=None, by_endpoint=None):
        """
        Decorator to apply rate limiting to a route.
        
        Args:
            requests (int, optional): Number of requests allowed in the time period
            period (int, optional): Time period in seconds
            by_endpoint (bool, optional): Whether to limit by endpoint or globally
            
        Returns:
            function: Decorated route function
        """
        # Use provided values or defaults
        requests = requests or self.default_limits['requests']
        period = period or self.default_limits['period']
        
        if by_endpoint is None:
            by_endpoint = self.default_limits['by_endpoint']
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get the rate limit key
                endpoint = f.__name__ if by_endpoint else None
                key = self._get_rate_limit_key(endpoint)
                
                # Get current usage
                count, reset_time = self._get_current_usage(key)
                
                # Check if limit exceeded
                if count >= requests:
                    # Calculate time until reset
                    retry_after = max(0, reset_time - int(time.time()))
                    
                    # Create rate limit response headers
                    headers = {
                        'X-RateLimit-Limit': str(requests),
                        'X-RateLimit-Remaining': '0',
                        'X-RateLimit-Reset': str(reset_time),
                        'Retry-After': str(retry_after)
                    }
                    
                    response = jsonify({
                        'status': 'error',
                        'error': 'Rate limit exceeded',
                        'retry_after': retry_after
                    })
                    response.status_code = 429  # Too Many Requests
                    
                    # Add headers to response
                    for key, value in headers.items():
                        response.headers[key] = value
                        
                    return response
                
                # Increment usage
                new_count, reset_time = self._increment_usage(key)
                
                # Execute the route function
                response = f(*args, **kwargs)
                
                # Add rate limit headers to the response
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(requests)
                    response.headers['X-RateLimit-Remaining'] = str(max(0, requests - new_count))
                    response.headers['X-RateLimit-Reset'] = str(reset_time)
                
                return response
            
            # Store original function for introspection
            decorated_function.__rate_limiter__ = True
            return decorated_function
        
        return decorator 