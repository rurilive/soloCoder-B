import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///survey.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400
    
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 86400
    
    SECURITY_CONTENT_TYPE_OPTIONS = 'nosniff'
    SECURITY_FRAME_OPTIONS = 'SAMEORIGIN'
    SECURITY_XSS_PROTECTION = '1; mode=block'
    
    RATELIMIT_DEFAULT = '1000/day;100/minute'
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_HEADERS_ENABLED = True
    
    LOGGING_LEVEL = 'INFO'
    LOG_SECURITY_EVENTS = True
    
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_COMPLEXITY = True

class DevelopmentConfig(Config):
    DEBUG = True
    
    SESSION_COOKIE_SECURE = False
    
    SECURITY_FRAME_OPTIONS = 'SAMEORIGIN'
    
    LOGGING_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    DEBUG = False
    
    SESSION_COOKIE_SECURE = True
    
    SECURITY_FRAME_OPTIONS = 'DENY'
    
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL') or 'memory://'
    
    LOGGING_LEVEL = 'WARNING'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    LOGGING_LEVEL = 'ERROR'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
