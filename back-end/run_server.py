#!/usr/bin/env python3
"""
Chess Game Server - OOP Refactored Version
Main entry point với cấu trúc OOP tách biệt handlers
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chess_server import ChessGameServer
from database import init_db
from config import SERVER_HOST, SERVER_PORT


def main():
    """Main entry point"""
    # Initialize database
    try:
        init_db()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    # Create server instance
    server = ChessGameServer(port=SERVER_PORT)
    
    # Start server
    if server.start():
        try:
            # Run event loop
            server.run_forever()
        except KeyboardInterrupt:
            server.stop()
    else:
        print("✗ Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
