"""
config.py - Application configuration
"""

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(32).hex())
    UPLOAD_DIR = os.environ.get('UPLOAD_DIR', '/tmp/deadrop_uploads')
    DB_PATH = os.environ.get('DB_PATH', 'deadrop.db')
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB
    DEFAULT_EXPIRY_HOURS = int(os.environ.get('DEFAULT_EXPIRY', 24))
    MAX_DOWNLOADS = int(os.environ.get('MAX_DOWNLOADS', 1))  # one-time by default
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', None)  # auto-generated if not set
