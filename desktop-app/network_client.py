"""
TCP Client Network Manager
Handles communication with C TCP server using the protocol defined in back-end/tcp_server/protocol.h
"""

import socket
import struct
import json
import threading
import queue
from enum import IntEnum
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal


class MessageTypeC2S(IntEnum):
    """Client to Server message types"""
    REGISTER = 0x0001
    LOGIN = 0x0002
    GET_ONLINE_USERS = 0x0003
    FIND_MATCH = 0x0010
    CANCEL_FIND_MATCH = 0x0011
    FIND_AI_MATCH = 0x0012
    MAKE_MOVE = 0x0020
    RESIGN = 0x0021
    OFFER_DRAW = 0x0022
    ACCEPT_DRAW = 0x0023
    DECLINE_DRAW = 0x0024
    GET_STATS = 0x0030
    GET_HISTORY = 0x0031
    GET_REPLAY = 0x0032


class MessageTypeS2C(IntEnum):
    """Server to Client message types"""
    REGISTER_RESULT = 0x1001
    LOGIN_RESULT = 0x1002
    USER_STATUS_UPDATE = 0x1003
    ONLINE_USERS_LIST = 0x1004
    MATCH_FOUND = 0x1100
    GAME_START = 0x1101
    GAME_STATE_UPDATE = 0x1200
    INVALID_MOVE = 0x1201
    GAME_OVER = 0x1202
    DRAW_OFFER_RECEIVED = 0x1203
    DRAW_OFFER_DECLINED = 0x1204
    STATS_RESPONSE = 0x1300
    HISTORY_RESPONSE = 0x1301
    REPLAY_DATA = 0x1302


class NetworkClient(QObject):
    """
    TCP Client with Qt Signals for UI integration
    Runs in a separate thread to avoid blocking UI
    """
    
    # Qt Signals for UI updates
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(int, dict)  # message_id, data
    error_occurred = pyqtSignal(str)
    
    def __init__(self, host='localhost', port=8765):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.connected_flag = False
        self.running = False
        
        # Worker thread
        self.receive_thread = None
        
        # Message handlers registry
        self.handlers: Dict[int, Callable] = {}
    
    def connect_to_server(self) -> bool:
        """Connect to the TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 5 second timeout for connection
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(None)  # Remove timeout for normal operation
            
            self.connected_flag = True
            self.running = True
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            self.connected.emit()
            return True
        
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            return False
    
    def disconnect_from_server(self):
        """Disconnect from server"""
        self.running = False
        self.connected_flag = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.disconnected.emit()
    
    def send_message(self, message_id: int, data: Dict[str, Any]) -> bool:
        """
        Send a message to the server
        
        Args:
            message_id: Message type ID (from MessageTypeC2S)
            data: Dictionary to send as JSON payload
            
        Returns:
            True if sent successfully
        """
        if not self.connected_flag or not self.socket:
            self.error_occurred.emit("Not connected to server")
            return False
        
        try:
            # Encode payload as JSON
            payload = json.dumps(data).encode('utf-8')
            payload_len = len(payload)
            
            # Pack header (network byte order: big-endian)
            # Format: !HI = unsigned short (2 bytes) + unsigned int (4 bytes)
            header = struct.pack('!HI', message_id, payload_len)
            
            # Send header + payload
            message = header + payload
            self.socket.sendall(message)
            
            return True
        
        except Exception as e:
            self.error_occurred.emit(f"Send failed: {e}")
            self.disconnect_from_server()
            return False
    
    def _receive_loop(self):
        """Background thread to receive messages"""
        while self.running and self.connected_flag:
            try:
                # Receive header (6 bytes)
                header = self._recv_exactly(6)
                if not header:
                    break
                
                # Unpack header
                message_id, payload_len = struct.unpack('!HI', header)
                
                # Receive payload
                payload = self._recv_exactly(payload_len)
                if not payload:
                    break
                
                # Decode JSON
                data = json.loads(payload.decode('utf-8'))
                
                # Emit signal to UI thread
                self.message_received.emit(message_id, data)
            
            except Exception as e:
                if self.running:
                    self.error_occurred.emit(f"Receive error: {e}")
                break
        
        # Disconnected
        if self.running:
            self.disconnect_from_server()
    
    def _recv_exactly(self, num_bytes: int) -> Optional[bytes]:
        """Receive exactly num_bytes from socket"""
        data = b''
        while len(data) < num_bytes:
            try:
                chunk = self.socket.recv(num_bytes - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data
    
    def register_handler(self, message_id: int, handler: Callable):
        """
        Register a handler for a specific message type
        
        Args:
            message_id: Message type ID (from MessageTypeS2C)
            handler: Callable with signature: handler(data: Dict)
        """
        self.handlers[message_id] = handler
    
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
    
    def get_stats(self):
        """Request user statistics"""
        return self.send_message(MessageTypeC2S.GET_STATS, {})
    
    def get_history(self):
        """Request game history"""
        return self.send_message(MessageTypeC2S.GET_HISTORY, {})
