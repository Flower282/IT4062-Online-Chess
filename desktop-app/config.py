"""
Configuration settings for Desktop App
Loads settings from environment variables with defaults
DPI-aware and cross-platform compatible
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

# Fixed window sizing - 960x600 pixels
MIN_APP_WIDTH = 960
MIN_APP_HEIGHT = 600
PREFERRED_APP_WIDTH = 960
PREFERRED_APP_HEIGHT = 600

# Font configuration - Cross-platform font families with fallbacks
FONT_FAMILY = "sans-serif"  # Qt will resolve to system default sans-serif
FONT_FAMILY_FALLBACK = ["Ubuntu", "Segoe UI", "Arial", "Helvetica", "sans-serif"]

# DPI scaling factors (will be auto-detected, but can be overridden)
DPI_SCALE_FACTOR = float(os.getenv('DPI_SCALE_FACTOR', '1.0'))

# Enable high DPI support
ENABLE_HIGH_DPI = os.getenv('ENABLE_HIGH_DPI', 'true').lower() == 'true'
