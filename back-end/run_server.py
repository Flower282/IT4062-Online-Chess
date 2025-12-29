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


def main():
    """Main entry point"""
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "CHESS GAME SERVER - OOP VERSION" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Initialize database
    print("=" * 80)
    print("  🔧 Initializing Database...")
    print("=" * 80)
    try:
        init_db()
        print("✓ Database connected and initialized\n")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("  Please check MongoDB connection and try again\n")
        sys.exit(1)
    
    # Create server instance
    print("=" * 80)
    print("  🚀 Starting Chess Game Server...")
    print("=" * 80)
    
    server = ChessGameServer(port=8765)
    
    # Start server
    if server.start():
        print("\n" + "=" * 80)
        print("  ✓ Server is running on port 8765")
        print("  Press Ctrl+C to stop")
        print("=" * 80)
        print()
        
        try:
            # Run event loop
            server.run_forever()
        except KeyboardInterrupt:
            print("\n\n⚠️  Shutting down server...")
            server.stop()
            print("✓ Server stopped gracefully")
    else:
        print("✗ Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
