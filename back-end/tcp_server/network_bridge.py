"""
Network Bridge - Python to C TCP Server Interface
This module provides a Python interface to the C TCP server using ctypes.
"""

import ctypes
import json
import os
from enum import IntEnum
from typing import Optional, Dict, Any, Callable
from pathlib import Path


# ========== Message Type Enums ==========

class MessageTypeC2S(IntEnum):
    """Client to Server message types"""
    REGISTER = 0x0001
    LOGIN = 0x0002
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


class EventType(IntEnum):
    """Network event types"""
    NEW_CONNECTION = 1
    CLIENT_DISCONNECTED = 2
    MESSAGE_RECEIVED = 3
    ERROR = 4


class ClientState(IntEnum):
    """Client connection states"""
    DISCONNECTED = 0
    CONNECTED = 1
    AUTHENTICATED = 2
    IN_GAME = 3


# ========== C Structure Definitions ==========

class MessageHeader(ctypes.Structure):
    """Message header structure (6 bytes)"""
    _pack_ = 1
    _fields_ = [
        ("message_id", ctypes.c_uint16),
        ("payload_length", ctypes.c_uint32)
    ]


class NetworkEvent(ctypes.Structure):
    """Network event structure"""
    _fields_ = [
        ("type", ctypes.c_int),
        ("client_fd", ctypes.c_int),
        ("message_id", ctypes.c_uint16),
        ("payload_length", ctypes.c_uint32),
        ("payload_data", ctypes.POINTER(ctypes.c_uint8))
    ]


class ClientSession(ctypes.Structure):
    """Client session structure"""
    _fields_ = [
        ("fd", ctypes.c_int),
        ("state", ctypes.c_int),
        ("recv_buffer", ctypes.c_uint8 * 65536),
        ("recv_offset", ctypes.c_size_t),
        ("send_buffer", ctypes.c_uint8 * 65536),
        ("send_offset", ctypes.c_size_t),
        ("send_length", ctypes.c_size_t),
        ("username", ctypes.c_char * 64),
        ("user_id", ctypes.c_uint32),
        ("game_id", ctypes.c_int)
    ]


# ========== Network Manager Class ==========

class NetworkManager:
    """
    Manages the C TCP server and provides Python interface for message handling.
    """
    
    def __init__(self, library_path: str = None):
        """
        Initialize the network manager.
        
        Args:
            library_path: Path to the compiled shared library (.so file)
        """
        if library_path is None:
            # Try to find the .so file in the same directory
            current_dir = Path(__file__).parent
            library_path = str(current_dir / "libchess_server.so")
        
        if not os.path.exists(library_path):
            raise FileNotFoundError(f"Shared library not found: {library_path}")
        
        # Load the shared library
        self.lib = ctypes.CDLL(library_path)
        
        # Define function signatures
        self._setup_function_signatures()
        
        # Message handlers
        self.handlers: Dict[int, Callable] = {}
        
        # Client session tracking
        self.client_sessions: Dict[int, Dict[str, Any]] = {}
    
    def _setup_function_signatures(self):
        """Setup ctypes function signatures for C library"""
        
        # int server_init(int port)
        self.lib.server_init.argtypes = [ctypes.c_int]
        self.lib.server_init.restype = ctypes.c_int
        
        # void server_shutdown(void)
        self.lib.server_shutdown.argtypes = []
        self.lib.server_shutdown.restype = None
        
        # int server_poll(int timeout_ms)
        self.lib.server_poll.argtypes = [ctypes.c_int]
        self.lib.server_poll.restype = ctypes.c_int
        
        # int send_message(int client_fd, uint16_t message_id, const uint8_t* payload, uint32_t payload_length)
        self.lib.send_message.argtypes = [
            ctypes.c_int,
            ctypes.c_uint16,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32
        ]
        self.lib.send_message.restype = ctypes.c_int
        
        # NetworkEvent* get_next_event(void)
        self.lib.get_next_event.argtypes = []
        self.lib.get_next_event.restype = ctypes.POINTER(NetworkEvent)
        
        # void free_event(NetworkEvent* event)
        self.lib.free_event.argtypes = [ctypes.POINTER(NetworkEvent)]
        self.lib.free_event.restype = None
        
        # ClientSession* get_client_session(int client_fd)
        self.lib.get_client_session.argtypes = [ctypes.c_int]
        self.lib.get_client_session.restype = ctypes.POINTER(ClientSession)
        
        # void disconnect_client(int client_fd)
        self.lib.disconnect_client.argtypes = [ctypes.c_int]
        self.lib.disconnect_client.restype = None
        
        # int get_client_count(void)
        self.lib.get_client_count.argtypes = []
        self.lib.get_client_count.restype = ctypes.c_int
        
        # const char* get_message_type_name(uint16_t message_id)
        self.lib.get_message_type_name.argtypes = [ctypes.c_uint16]
        self.lib.get_message_type_name.restype = ctypes.c_char_p
    
    def start(self, port: int) -> bool:
        """
        Start the TCP server on the specified port.
        
        Args:
            port: Port number to listen on
            
        Returns:
            True if server started successfully, False otherwise
        """
        result = self.lib.server_init(port)
        if result == 0:
            print(f"✓ TCP Server started on port {port}")
            return True
        else:
            print(f"✗ Failed to start TCP server on port {port}")
            return False
    
    def stop(self):
        """Stop the TCP server and cleanup resources"""
        self.lib.server_shutdown()
        print("✓ TCP Server stopped")
    
    def poll(self, timeout_ms: int = 100) -> int:
        """
        Poll for network events.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Number of events or -1 on error
        """
        return self.lib.server_poll(timeout_ms)
    
    def send_to_client(self, client_fd: int, message_type: int, data: Dict[str, Any]) -> bool:
        """
        Send a message to a client.
        
        Args:
            client_fd: Client file descriptor
            message_type: Message type ID (from MessageTypeS2C)
            data: Dictionary containing message data (will be JSON encoded)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        # Convert data to JSON
        payload_str = json.dumps(data)
        payload_bytes = payload_str.encode('utf-8')
        payload_length = len(payload_bytes)
        
        # Create ctypes array
        payload_array = (ctypes.c_uint8 * payload_length)(*payload_bytes)
        
        # Send message
        result = self.lib.send_message(
            client_fd,
            message_type,
            payload_array,
            payload_length
        )
        
        return result > 0
    
    def process_events(self) -> bool:
        """
        Process all pending network events.
        
        Returns:
            True if events were processed, False if no events
        """
        had_events = False
        
        while True:
            # Get next event
            event_ptr = self.lib.get_next_event()
            if not event_ptr:
                break
            
            had_events = True
            event = event_ptr.contents
            
            try:
                if event.type == EventType.NEW_CONNECTION:
                    self._handle_new_connection(event)
                
                elif event.type == EventType.CLIENT_DISCONNECTED:
                    self._handle_client_disconnected(event)
                
                elif event.type == EventType.MESSAGE_RECEIVED:
                    self._handle_message_received(event)
                
                elif event.type == EventType.ERROR:
                    self._handle_error(event)
            
            finally:
                # Free the event
                self.lib.free_event(event_ptr)
        
        return had_events
    
    def _handle_new_connection(self, event: NetworkEvent):
        """Handle new client connection"""
        client_fd = event.client_fd
        self.client_sessions[client_fd] = {
            'fd': client_fd,
            'state': ClientState.CONNECTED,
            'authenticated': False,
            'username': None,
            'user_id': None,
            'game_id': None
        }
        print(f"→ New connection: fd={client_fd}")
    
    def _handle_client_disconnected(self, event: NetworkEvent):
        """Handle client disconnection"""
        client_fd = event.client_fd
        if client_fd in self.client_sessions:
            session = self.client_sessions[client_fd]
            print(f"← Client disconnected: fd={client_fd}, user={session.get('username', 'N/A')}")
            del self.client_sessions[client_fd]
    
    def _handle_message_received(self, event: NetworkEvent):
        """Handle received message from client"""
        client_fd = event.client_fd
        message_id = event.message_id
        
        # Extract payload
        payload_data = None
        if event.payload_length > 0 and event.payload_data:
            payload_bytes = bytes(event.payload_data[:event.payload_length])
            try:
                payload_str = payload_bytes.decode('utf-8')
                payload_data = json.loads(payload_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"✗ Failed to decode payload: {e}")
                payload_data = {}
        else:
            payload_data = {}
        
        # Get message type name
        msg_name = self.lib.get_message_type_name(message_id).decode('utf-8')
        print(f"← Message from fd={client_fd}: {msg_name} (0x{message_id:04x})")
        
        # Call registered handler
        if message_id in self.handlers:
            try:
                self.handlers[message_id](client_fd, payload_data)
            except Exception as e:
                print(f"✗ Error in message handler: {e}")
        else:
            print(f"⚠ No handler registered for message type: {msg_name}")
    
    def _handle_error(self, event: NetworkEvent):
        """Handle error event"""
        print(f"✗ Network error: fd={event.client_fd}")
    
    def register_handler(self, message_type: int, handler: Callable):
        """
        Register a message handler.
        
        Args:
            message_type: Message type ID (from MessageTypeC2S)
            handler: Callable with signature: handler(client_fd: int, data: Dict)
        """
        self.handlers[message_type] = handler
    
    def get_client_info(self, client_fd: int) -> Optional[Dict[str, Any]]:
        """
        Get client session information.
        
        Args:
            client_fd: Client file descriptor
            
        Returns:
            Client session dict or None if not found
        """
        return self.client_sessions.get(client_fd)
    
    def update_client_session(self, client_fd: int, **kwargs):
        """
        Update client session information.
        
        Args:
            client_fd: Client file descriptor
            **kwargs: Fields to update in session
        """
        if client_fd in self.client_sessions:
            self.client_sessions[client_fd].update(kwargs)
    
    def disconnect_client(self, client_fd: int):
        """
        Disconnect a client.
        
        Args:
            client_fd: Client file descriptor
        """
        self.lib.disconnect_client(client_fd)
    
    def get_client_count(self) -> int:
        """
        Get number of connected clients.
        
        Returns:
            Number of connected clients
        """
        return self.lib.get_client_count()
    
    def run_forever(self, poll_timeout_ms: int = 100):
        """
        Run the server event loop forever.
        
        Args:
            poll_timeout_ms: Poll timeout in milliseconds
        """
        print("✓ Server event loop started")
        try:
            while True:
                # Poll for events
                self.poll(poll_timeout_ms)
                
                # Process events
                self.process_events()
        
        except KeyboardInterrupt:
            print("\n⚠ Server interrupted by user")
        finally:
            self.stop()


# ========== Example Usage ==========

if __name__ == "__main__":
    # Create network manager
    manager = NetworkManager()
    
    # Define message handlers
    def handle_login(client_fd: int, data: Dict):
        username = data.get('username', '')
        password = data.get('password', '')
        
        print(f"Login attempt: {username}")
        
        # TODO: Validate credentials with database
        # For now, accept all logins
        
        # Update session
        manager.update_client_session(
            client_fd,
            authenticated=True,
            username=username,
            user_id=12345
        )
        
        # Send login result
        manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
            'success': True,
            'user_id': 12345,
            'username': username,
            'rating': 1500
        })
    
    def handle_register(client_fd: int, data: Dict):
        username = data.get('username', '')
        password = data.get('password', '')
        email = data.get('email', '')
        
        print(f"Register attempt: {username}")
        
        # TODO: Create user in database
        
        # Send register result
        manager.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
            'success': True,
            'message': 'Account created successfully'
        })
    
    def handle_find_match(client_fd: int, data: Dict):
        print(f"Find match request from fd={client_fd}")
        
        # TODO: Add to matchmaking queue
        
        # For demo, immediately send match found
        manager.send_to_client(client_fd, MessageTypeS2C.MATCH_FOUND, {
            'opponent_id': 67890,
            'opponent_username': 'TestOpponent',
            'opponent_rating': 1520,
            'game_id': 'game_12345'
        })
    
    # Register handlers
    manager.register_handler(MessageTypeC2S.LOGIN, handle_login)
    manager.register_handler(MessageTypeC2S.REGISTER, handle_register)
    manager.register_handler(MessageTypeC2S.FIND_MATCH, handle_find_match)
    
    # Start server
    if manager.start(port=8765):
        # Run event loop
        manager.run_forever()
