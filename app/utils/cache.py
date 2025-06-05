import os
import pickle
import threading
import logging

# Import time constants from config
from app.config import ONE_MINUTE, ONE_HOUR, ONE_DAY, DEFAULT_CACHE_TIMEOUT

# Default cache settings
DEFAULT_KEY_PREFIX = 'amazon_book_image'
DEFAULT_CACHE_FILE = 'book_image_cache.pkl'

try:
    import redis
except ImportError:
    redis = None

class BookImageCache:
    def __init__(self, config):
        self.lock = threading.Lock()
        self.redis_url = config.get('CACHE_REDIS_URL')
        
        # Get timeout from CACHE_TIMEOUT in config, default to 1 hour if not found
        try:
            self.timeout = int(config.get('CACHE_TIMEOUT', DEFAULT_CACHE_TIMEOUT))
        except (TypeError, ValueError):
            self.timeout = DEFAULT_CACHE_TIMEOUT
        
        # Format timeout for better readability
        if self.timeout >= ONE_DAY:
            timeout_str = f"{self.timeout/ONE_DAY:.1f} days ({self.timeout} seconds)"
        elif self.timeout >= ONE_HOUR:
            timeout_str = f"{self.timeout/ONE_HOUR:.1f} hours ({self.timeout} seconds)"
        elif self.timeout >= ONE_MINUTE:
            timeout_str = f"{self.timeout/ONE_MINUTE:.1f} minutes ({self.timeout} seconds)"
        else:
            timeout_str = f"{self.timeout} seconds"
            
        logging.warning(f"[CACHE][CONFIG] Using cache timeout: {timeout_str}")
        
        # Initialize cache backend
        self.use_redis = False
        self.redis_client = None
        self.key_prefix = config.get('CACHE_KEY_PREFIX', DEFAULT_KEY_PREFIX)
        self.file_db_path = os.path.join(os.path.dirname(__file__), DEFAULT_CACHE_FILE)
        
        # Try to connect to Redis if available
        logging.warning(f"[CACHE][INIT] redis module: {redis}, redis_url: {self.redis_url}")
        if redis and self.redis_url and self.redis_url.startswith('redis://'):
            logging.warning("[CACHE][INIT] Attempting to connect to Redis...")
            try:
                self.redis_client = redis.StrictRedis.from_url(self.redis_url)
                self.redis_client.ping()  # Test connection
                self.use_redis = True
                logging.warning("[CACHE][INIT] Redis connection successful. Using Redis for caching.")
            except Exception as e:
                logging.error(f"[CACHE][INIT] Redis connection failed: {e}. Falling back to file-based caching.")
                self.use_redis = False
        else:
            logging.warning("[CACHE][INIT] Redis not used (missing redis-py, no URL, or bad URL). Using file-based cache.")

    def get(self, book_url):
        key = f"{self.key_prefix}:{book_url}"
        backend = 'redis' if self.use_redis else 'file'
        print(f"[CACHE][GET] Backend: {backend}, Key: {key}")
        
        if self.use_redis:
            result = self.redis_client.get(key)
            if result:
                print(f"[CACHE][GET] HIT for key: {key}")
                return result.decode()
            else:
                print(f"[CACHE][GET] MISS for key: {key}")
                return None
        else:
            # File-based cache
            with self.lock:
                # Check if cache file exists
                if not os.path.exists(self.file_db_path):
                    print(f"[CACHE][GET] MISS (cache file not found) for key: {key}")
                    return None
                    
                # Load cache from file
                with open(self.file_db_path, 'rb') as f:
                    cache = pickle.load(f)
                    
                # Check if key exists in cache
                if key in cache:
                    print(f"[CACHE][GET] HIT for key: {key}")
                else:
                    print(f"[CACHE][GET] MISS for key: {key}")
                    
                return cache.get(key)

    def set(self, book_url, image_url):
        key = f"{self.key_prefix}:{book_url}"
        backend = 'redis' if self.use_redis else 'file'
        print(f"[CACHE][SET] Backend: {backend}, Key: {key}")
        if self.use_redis:
            logging.warning(f"[CACHE][REDIS] Setting key {key} with timeout: {self.timeout} seconds")
            self.redis_client.setex(key, self.timeout, image_url)
        else:
            with self.lock:
                cache = {}
                if os.path.exists(self.file_db_path):
                    with open(self.file_db_path, 'rb') as f:
                        cache = pickle.load(f)
                cache[key] = image_url
                with open(self.file_db_path, 'wb') as f:
                    pickle.dump(cache, f)
