import os
from dotenv import load_dotenv
load_dotenv()

# Constants for default values
# Time constants in seconds
ONE_MINUTE = 60
ONE_HOUR = 3600
ONE_DAY = 86400
ONE_WEEK = 604800
ONE_MONTH = 2592000
ONE_YEAR = 31536000

# Default cache settings
DEFAULT_CACHE_TYPE = 'simple'
DEFAULT_REDIS_URL = 'redis://localhost:6379/0'
DEFAULT_CACHE_TIMEOUT = ONE_YEAR

class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = False
    TESTING = False
    
    # API settings
    API_TITLE = 'Amazon Book Image API'
    API_VERSION = 'v1'
    
    # Cache settings
    CACHE_TYPE = os.environ.get('CACHE_TYPE', DEFAULT_CACHE_TYPE)
    CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL', DEFAULT_REDIS_URL)
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', DEFAULT_CACHE_TIMEOUT))
    
    # Rate limiting
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # Scraper settings
    REQUEST_TIMEOUT = (
        float(os.environ.get('REQUEST_CONNECT_TIMEOUT', 3.05)),
        float(os.environ.get('REQUEST_READ_TIMEOUT', 6.05))
    )
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.58'
    ]
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', None)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    # Ensure SECRET_KEY is set for production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # In production, we should use Redis for caching
    CACHE_TYPE = 'redis'
    
    # Use file logging in production
    LOG_FILE = os.environ.get('LOG_FILE', '/var/log/amazon-book-api/app.log')


# Dictionary of configurations
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Get configuration based on environment
def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
