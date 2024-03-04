import os
from redis import StrictRedis
from functools import wraps

redis_client = StrictRedis(
    host=os.getenv('REDIS_CACHE_HOST', 'localhost'),
    port=os.getenv('REDIS_CACHE_PORT', 6379),
    db=1,
    decode_responses=True
)

def generate_cache_key(func, *args, **kwargs):
    args_str = ','.join(map(str, args))
    kwargs_str = ','.join([f"{key}={value}" for key, value in sorted(kwargs.items())])
    return f"{func.__name__}:{args_str}:{kwargs_str}"

def redis_cache(ttl=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(func, *args, **kwargs)
            cached_result = redis_client.get(cache_key)

            if cached_result:
                return cached_result.decode('utf-8')
            else:
                result = func(*args, **kwargs)
                redis_client.setex(cache_key, ttl, result)
                return result
            
        return wrapper
    return decorator

