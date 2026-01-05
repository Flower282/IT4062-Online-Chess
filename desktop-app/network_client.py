"""
TCP Client Network Manager
Qt wrapper around NetworkBridge for UI integration
"""

from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from network_bridge_client import NetworkBridge, MessageTypeC2S, MessageTypeS2C, EventType
from config import SERVER_HOST, SERVER_PORT


class NetworkClient(QObject):
    """
    TCP Client with Qt Signals for UI integration.
    Wraps NetworkBridge to provide Qt signals and high-level API.
    """
    
    # Qt Signals for UI updates
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(int, dict)  # message_id, data
    error_occurred = pyqtSignal(str)
    
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        super().__init__()
        self.host = host
        self.port = port
        
        # Create network bridge
        self.bridge = NetworkBridge()
        
        # Register bridge event handlers
        self._register_bridge_handlers()
        
        # Timer for polling events
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_events)
    
    def _register_bridge_handlers(self):
        """Register handlers with the bridge to convert to Qt signals"""
        
        # Connection events
        self.bridge.register_handler(EventType.CONNECTED, self._on_connected)
        self.bridge.register_handler(EventType.DISCONNECTED, self._on_disconnected)
        self.bridge.register_handler(EventType.ERROR, self._on_error)
        
        # Register all S2C message handlers to emit Qt signals
        for msg_type in MessageTypeS2C:
            self.bridge.register_handler(msg_type.value, self._create_message_handler(msg_type.value))
    
    def _create_message_handler(self, message_id: int):
        """Create a message handler that emits Qt signal"""
        def handler(data: Dict[str, Any]):
            self.message_received.emit(message_id, data)
        return handler
    
    def _on_connected(self):
        """Bridge callback: connection established"""
        self.connected.emit()
    
    def _on_disconnected(self):
        """Bridge callback: disconnected"""
        self.disconnected.emit()
        self.poll_timer.stop()
    
    def _on_error(self):
        """Bridge callback: error occurred"""
        self.error_occurred.emit("Network error")
    
    def connect_to_server(self) -> bool:
        """Connect to the TCP server"""
        try:
            result = self.bridge.connect(self.host, self.port)
            if result:
                # Start polling for events
                self.poll_timer.start(50)  # Poll every 50ms
            return result
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            return False
    
    def disconnect_from_server(self):
        """Disconnect from server"""
        self.poll_timer.stop()
        self.bridge.disconnect()
    
    def is_connected(self) -> bool:
        """
        Check if connected to server.
        
        Returns:
            True if connected, False otherwise
        """
        return self.bridge.is_connected()
    
    def _poll_events(self):
        """Poll for events from bridge (called by QTimer)"""
        # Poll C library through bridge
        self.bridge.poll(10)  # 10ms timeout
        
        # Process all pending events
        self.bridge.process_events()
    
    def send_message(self, message_id: int, data: Dict[str, Any]) -> bool:
        """
        Send a message to the server.
        
        Args:
            message_id: Message type ID (from MessageTypeC2S)
            data: Dictionary to send as JSON payload
            
        Returns:
            True if sent successfully
        """
        return self.bridge.send_message(message_id, data)
    
    def register_handler(self, message_id: int, handler: Callable):
        """
        Register an additional handler for a specific message type.
        Handler will be called when message is received, and Qt signal will also be emitted.
        
        Note: This adds a custom handler alongside the default Qt signal emission.
        
        Args:
            message_id: Message type ID (from MessageTypeS2C)
            handler: Callable with signature: handler(data: Dict)
        """
        # Create a wrapper that calls both the signal emission and custom handler
        def wrapped_handler(data: Dict[str, Any]):
            self.message_received.emit(message_id, data)
            handler(data)
        
        self.bridge.register_handler(message_id, wrapped_handler)
    
    # High-level API methods
    
    def login(self, username: str, password: str):
        """Send login request"""
        return self.send_message(MessageTypeC2S.LOGIN, {
            'username': username,
            'password': password
        })
    
    def register(self, username: str, password: str, email: str):
        """Send registration request"""
        return self.send_message(MessageTypeC2S.REGISTER, {
            'username': username,
            'password': password,
            'email': email
        })
    
    def get_online_users(self):
        """Get list of online users"""
        return self.send_message(MessageTypeC2S.GET_ONLINE_USERS, {})
    
    def find_match(self):
        """Request matchmaking"""
        return self.send_message(MessageTypeC2S.FIND_MATCH, {})
    
    def cancel_find_match(self):
        """Cancel matchmaking"""
        return self.send_message(MessageTypeC2S.CANCEL_FIND_MATCH, {})
    
    def find_ai_match(self, difficulty: str = 'medium'):
        """Request AI match"""
        return self.send_message(MessageTypeC2S.FIND_AI_MATCH, {
            'difficulty': difficulty
        })
    
    def make_move(self, game_id: str, from_square: str, to_square: str, promotion: str = None):
        """Make a chess move (UCI format)"""
        # Convert to UCI format: e2e4, e7e5q (with promotion)
        uci_move = from_square + to_square
        if promotion:
            uci_move += promotion
        
        print(f"📤 Sending move to server: {uci_move} (game: {game_id})")
        
        move_data = {
            'game_id': game_id,
            'move': uci_move
        }
        
        return self.send_message(MessageTypeC2S.MAKE_MOVE, move_data)
    
    def resign(self, game_id: str):
        """Resign from game"""
        return self.send_message(MessageTypeC2S.RESIGN, {'game_id': game_id})
    
    def offer_draw(self, game_id: str):
        """Offer draw"""
        return self.send_message(MessageTypeC2S.OFFER_DRAW, {'game_id': game_id})
    
    def accept_draw(self):
        """Accept draw offer"""
        return self.send_message(MessageTypeC2S.ACCEPT_DRAW, {})
    
    def decline_draw(self):
        """Decline draw offer"""
        return self.send_message(MessageTypeC2S.DECLINE_DRAW, {})
    
    def challenge_player(self, opponent_user_id: int, opponent_username: str):
        """Send challenge to specific player"""
        return self.send_message(MessageTypeC2S.CHALLENGE, {
            'opponent_user_id': opponent_user_id,
            'opponent_username': opponent_username
        })
    
    def accept_challenge(self, challenger_id: int):
        """Accept challenge from another player"""
        return self.send_message(MessageTypeC2S.ACCEPT_CHALLENGE, {
            'challenger_id': challenger_id
        })
    
    def decline_challenge(self, challenger_id: int):
        """Decline challenge from another player"""
        return self.send_message(MessageTypeC2S.DECLINE_CHALLENGE, {
            'challenger_id': challenger_id
        })
    
    def get_stats(self):
        """Request user statistics"""
        return self.send_message(MessageTypeC2S.GET_STATS, {})
    
    def get_history(self):
        """Request game history"""
        return self.send_message(MessageTypeC2S.GET_HISTORY, {})
