"""
Configuration settings for Desktop App
Loads settings from environment variables with defaults
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Server configuration
SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.getenv('SERVER_PORT', '8765'))

# Application settings
APP_TITLE = "Chess Desktop App"
APP_WIDTH = 1280
APP_HEIGHT = 853
