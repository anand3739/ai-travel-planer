import time
import json
import hashlib

# In-memory storage: { key: { "data": ..., "timestamp": ... } }
_cache = {}
# TTL = 10 minutes (600 seconds)
TTL_SECONDS = 600

def generate_cache_key(function_name, params):
    """Generate a unique string key based on function name and arguments."""
    # Serialize parameters to a stable JSON string
    param_str = json.dumps(params, sort_keys=True)
    raw_key = f"{function_name}:{param_str}"
    # Use MD5 for a slightly cleaner/shorter key string
    return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

def get_cache(key):
    """Retrieve data if present and not expired."""
    entry = _cache.get(key)
    if not entry:
        return None
    
    # Check TTL
    if time.time() - entry["timestamp"] > TTL_SECONDS:
        # Expired, clean up
        del _cache[key]
        return None
    
    return entry["data"]

def set_cache(key, data):
    """Store data with current timestamp."""
    _cache[key] = {
        "data": data,
        "timestamp": time.time()
    }

def delete_cache(key):
    """Remove a specific cache entry, if it exists."""
    _cache.pop(key, None)
