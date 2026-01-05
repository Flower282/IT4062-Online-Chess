"""
Network Bridge Client - Python to C TCP Client Interface
Pure bridge layer without Qt dependencies
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
    GET_ONLINE_USERS = 0x0003
    FIND_MATCH = 0x0010
    CANCEL_FIND_MATCH = 0x0011
    FIND_AI_MATCH = 0x0012
    MAKE_MOVE = 0x0020
    RESIGN = 0x0021
    OFFER_DRAW = 0x0022
    ACCEPT_DRAW = 0x0023
    DECLINE_DRAW = 0x0024
    CHALLENGE = 0x0025
    ACCEPT_CHALLENGE = 0x0026
    DECLINE_CHALLENGE = 0x0027
    GET_STATS = 0x0030
    GET_HISTORY = 0x0031


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
    CHALLENGE_RECEIVED = 0x1205
    CHALLENGE_ACCEPTED = 0x1206
    CHALLENGE_DECLINED = 0x1207
    STATS_RESPONSE = 0x1300
    HISTORY_RESPONSE = 0x1301


class EventType(IntEnum):
    """Network event types"""
    CONNECTED = 1
    DISCONNECTED = 2
    MESSAGE_RECEIVED = 3
    ERROR = 4


# ========== C Structure Definitions ==========

class NetworkEvent(ctypes.Structure):
    """Network event structure"""
    _fields_ = [
        ("type", ctypes.c_int),
        ("message_id", ctypes.c_uint16),
        ("payload_length", ctypes.c_uint32),
        ("payload_data", ctypes.POINTER(ctypes.c_uint8))
    ]


# ========== Network Bridge Class ==========

class NetworkBridge:
    """
    Pure network bridge between Python and C TCP client library.
    No Qt dependencies - just ctypes interface.
    """
    
    def __init__(self, library_path: str = None):
        """
        Initialize the network bridge.
        
        Args:
            library_path: Path to the compiled shared library (.so file)
        """
        if library_path is None:
            current_dir = Path(__file__).parent
            library_path = str(current_dir / "tcp_client" / "libchess_client.so")
        
        if not os.path.exists(library_path):
            raise FileNotFoundError(f"Shared library not found: {library_path}")
        
        # Load the shared library
        self.lib = ctypes.CDLL(library_path)
        
        # Define function signatures
        self._setup_function_signatures()
        
        # Message handlers
        self.handlers: Dict[int, Callable] = {}
        
        # Connection info
        self.host = None
        self.port = None
    
    def _setup_function_signatures(self):
        """Setup ctypes function signatures for C library"""
        
        # int client_init(const char* host, int port)
        self.lib.client_init.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.client_init.restype = ctypes.c_int
        
        # void client_shutdown(void)
        self.lib.client_shutdown.argtypes = []
        self.lib.client_shutdown.restype = None
        
        # int client_poll(int timeout_ms)
        self.lib.client_poll.argtypes = [ctypes.c_int]
        self.lib.client_poll.restype = ctypes.c_int
        
        # int client_send_message(uint16_t message_id, const uint8_t* payload, uint32_t payload_length)
        self.lib.client_send_message.argtypes = [
            ctypes.c_uint16,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint32
        ]
        self.lib.client_send_message.restype = ctypes.c_int
        
        # NetworkEvent* get_next_event(void)
        self.lib.get_next_event.argtypes = []
        self.lib.get_next_event.restype = ctypes.POINTER(NetworkEvent)
        
        # void free_event(NetworkEvent* event)
        self.lib.free_event.argtypes = [ctypes.POINTER(NetworkEvent)]
        self.lib.free_event.restype = None
        
        # int is_connected(void)
        self.lib.is_connected.argtypes = []
        self.lib.is_connected.restype = ctypes.c_int
        
        # const char* get_message_type_name(uint16_t message_id)
        self.lib.get_message_type_name.argtypes = [ctypes.c_uint16]
        self.lib.get_message_type_name.restype = ctypes.c_char_p
    
    def connect(self, host: str, port: int) -> bool:
        """
        Connect to the TCP server.
        
        Args:
            host: Server hostname or IP
            port: Server port number
            
        Returns:
            True if connected successfully, False otherwise
        """
        self.host = host
        self.port = port
        
        host_bytes = host.encode('utf-8')
        result = self.lib.client_init(host_bytes, port)
        
        if result == 0:
            return True
        else:
            return False
    
    def disconnect(self):
        """Disconnect from server and cleanup"""
        self.lib.client_shutdown()
    
    def poll(self, timeout_ms: int = 10) -> int:
        """
        Poll for network events.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Number of events or -1 on error
        """
        return self.lib.client_poll(timeout_ms)
    
    def send_message(self, message_id: int, data: Dict[str, Any]) -> bool:
        """
        Send a message to the server.
        
        Args:
            message_id: Message type ID (from MessageTypeC2S)
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
        result = self.lib.client_send_message(
            message_id,
            payload_array,
            payload_length
        )
        
        if result > 0:
            msg_name = self.lib.get_message_type_name(message_id).decode('utf-8')
            print(f"→ Sent: {msg_name} (0x{message_id:04x})")
            return True
        else:
            print(f"✗ Failed to send message: 0x{message_id:04x}")
            return False
    
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
                if event.type == EventType.CONNECTED:
                    self._handle_connected(event)
                
                elif event.type == EventType.DISCONNECTED:
                    self._handle_disconnected(event)
                
                elif event.type == EventType.MESSAGE_RECEIVED:
                    self._handle_message_received(event)
                
                elif event.type == EventType.ERROR:
                    self._handle_error(event)
            
            finally:
                # Free the event
                self.lib.free_event(event_ptr)
        
        return had_events
    
    def _handle_connected(self, event: NetworkEvent):
        """Handle connection established event"""
        print(f"→ Connected event")
        if EventType.CONNECTED in self.handlers:
            self.handlers[EventType.CONNECTED]()
    
    def _handle_disconnected(self, event: NetworkEvent):
        """Handle disconnection event"""
        print(f"← Disconnected event")
        if EventType.DISCONNECTED in self.handlers:
            self.handlers[EventType.DISCONNECTED]()
    
    def _handle_message_received(self, event: NetworkEvent):
        """Handle received message from server"""
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
        print(f"← Received: {msg_name} (0x{message_id:04x})")
        
        # Call registered handler
        if message_id in self.handlers:
            try:
                self.handlers[message_id](payload_data)
            except Exception as e:
                print(f"✗ Error in message handler: {e}")
        else:
            print(f"⚠ No handler registered for message type: {msg_name}")
    
    def _handle_error(self, event: NetworkEvent):
        """Handle error event"""
        print(f"✗ Network error event")
        if EventType.ERROR in self.handlers:
            self.handlers[EventType.ERROR]()
    
    def register_handler(self, message_type: int, handler: Callable):
        """
        Register a message handler.
        
        Args:
            message_type: Message type ID (from MessageTypeS2C or EventType)
            handler: Callable with signature: handler(data: Dict) for messages
                     or handler() for events (CONNECTED, DISCONNECTED, ERROR)
        """
        self.handlers[message_type] = handler
    
    def is_connected(self) -> bool:
        """
        Check if connected to server.
        
        Returns:
            True if connected, False otherwise
        """
        return bool(self.lib.is_connected())
    
    def get_message_type_name(self, message_id: int) -> str:
        """
        Get human-readable name for message type.
        
        Args:
            message_id: Message type ID
            
        Returns:
            Message type name string
        """
        return self.lib.get_message_type_name(message_id).decode('utf-8')
