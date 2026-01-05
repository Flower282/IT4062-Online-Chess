"""
Chess Game Server
Main server class kết hợp NetworkManager và các handlers
"""

from database import init_db
from tcp_server.network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C
from handlers import AuthHandler, GameHandler, MatchmakingHandler, StatsHandler
from ml.model_loader import load_model
import time
from config import SERVER_PORT


class ChessGameServer:
    """
    Main Chess Game Server class
    Kết hợp network layer và game logic
    """
    
    def __init__(self, port=SERVER_PORT):
        """
        Initialize Chess Game Server
        
        Args:
            port: TCP port to listen on
        """
        self.port = port
        
        # Initialize network manager
        self.network = NetworkManager()
        
        # Load ML model
        self.model = load_model()

        # Initialize handlers
        self.auth_handler = AuthHandler(self.network)
        self.matchmaking_handler = MatchmakingHandler(self.network)
        self.game_handler = GameHandler(self.network, self.matchmaking_handler, self.model)
        self.stats_handler = StatsHandler(self.network)
        
        # Set MessageTypeS2C for all handlers (including win_handler inside game_handler)
        for handler in [self.auth_handler, self.matchmaking_handler, 
                       self.game_handler, self.stats_handler]:
            handler.MessageTypeS2C = MessageTypeS2C
        
        # Set MessageTypeS2C for win_handler
        self.game_handler.win_handler.MessageTypeS2C = MessageTypeS2C
        
        # Register all message handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message handlers with NetworkManager"""
        
        # Authentication handlers (0x0001, 0x0002, 0x0003)
        self.network.register_handler(MessageTypeC2S.REGISTER, self.auth_handler.handle_register)
        self.network.register_handler(MessageTypeC2S.LOGIN, self.auth_handler.handle_login)
        self.network.register_handler(MessageTypeC2S.GET_ONLINE_USERS, self.auth_handler.handle_get_online_users)
        
        # Matchmaking handlers (0x0010, 0x0011, 0x0012)
        self.network.register_handler(MessageTypeC2S.FIND_MATCH, self.matchmaking_handler.handle_find_match)
        self.network.register_handler(MessageTypeC2S.CANCEL_FIND_MATCH, self.matchmaking_handler.handle_cancel_find_match)
        self.network.register_handler(MessageTypeC2S.FIND_AI_MATCH, self.matchmaking_handler.handle_find_ai_match)
        
        # Game handlers (0x0020-0x0024)
        self.network.register_handler(MessageTypeC2S.MAKE_MOVE, self.game_handler.handle_make_move)
        self.network.register_handler(MessageTypeC2S.RESIGN, self.game_handler.handle_resign)
        self.network.register_handler(MessageTypeC2S.OFFER_DRAW, self.game_handler.handle_offer_draw)
        self.network.register_handler(MessageTypeC2S.ACCEPT_DRAW, self.game_handler.handle_accept_draw)
        self.network.register_handler(MessageTypeC2S.DECLINE_DRAW, self.game_handler.handle_decline_draw)
        self.network.register_handler(MessageTypeC2S.CHALLENGE, self.matchmaking_handler.handle_challenge)
        self.network.register_handler(MessageTypeC2S.ACCEPT_CHALLENGE, self.matchmaking_handler.handle_accept_challenge)
        self.network.register_handler(MessageTypeC2S.DECLINE_CHALLENGE, self.matchmaking_handler.handle_decline_challenge)
        
        # Stats handlers (0x0030-0x0031)
        self.network.register_handler(MessageTypeC2S.GET_STATS, self.stats_handler.handle_get_stats)
        self.network.register_handler(MessageTypeC2S.GET_HISTORY, self.stats_handler.handle_get_history)
    
    def start(self):
        """Start the server"""
        if self.network.start(port=self.port):
            return True
        return False
    
    def stop(self):
        """Stop the server"""
        self.network.stop()
    
    def run_forever(self, poll_timeout_ms=100):
        """
        Run the server event loop
        
        Args:
            poll_timeout_ms: Poll timeout in milliseconds
        """
        print(f"✓ Server event loop started on port {self.port}")
        try:
            while True:
                # Poll for network events
                self.network.poll(poll_timeout_ms)
                
                # Process events
                self.network.process_events()
                
                # Check for game timeouts
                self.game_handler.check_timeouts()
                
        except KeyboardInterrupt:
            print("\n⚠ Server interrupted by user")
        finally:
            self.stop()


def main():
    """Main entry point"""
    # Initialize database
    print("=" * 60)
    print("  Initializing Database...")
    print("=" * 60)
    try:
        init_db()
        print("✓ Database ready\n")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("  Please check MongoDB connection and try again\n")
        sys.exit(1)
    
    # Create and start server
    server = ChessGameServer(port=SERVER_PORT)
    
    if server.start():
        # Run event loop
        server.run_forever()
    else:
        print("✗ Failed to start server")
        sys.exit(1)


if __name__ == "__main__":
    main()
