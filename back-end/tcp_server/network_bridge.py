"""
Network Bridge - Python to C TCP Server Interface
This module provides a Python interface to the C TCP server using ctypes.
"""

import ctypes
import json
import os
import sys
import time
from enum import IntEnum
from typing import Optional, Dict, Any, Callable
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_db_connection, init_db
from services.user_service import create_user, verify_user, get_user_by_username
from services.game_service import (
    create_game, get_game, update_game_state, end_game,
    get_user_game_history, get_user_stats, validate_move, get_game_pgn
)


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
    
    # Create network manager
    manager = NetworkManager()
    
    # Store active games and matchmaking queue
    active_games = {}
    matchmaking_queue = []
    
    # Define message handlers with database integration
    
    # 0x0001 - REGISTER: Quản lý người dùng: Yêu cầu đăng ký
    def handle_register(client_fd: int, data: Dict):
        username = data.get('username', '')
        password = data.get('password', '')
        email = data.get('email', '')
        fullname = data.get('fullname', username)
        
        print(f"📝 Register attempt: {username} ({email})")
        
        # Create user in database
        result = create_user(fullname=fullname, username=username, password=password)
        
        # Send register result (0x1001 - REGISTER_RESULT)
        manager.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
            'success': result['success'],
            'message': result['message']
        })
    
    # 0x0002 - LOGIN: Quản lý người dùng: Yêu cầu đăng nhập
    def handle_login(client_fd: int, data: Dict):
        username = data.get('email', '').split('@')[0] if '@' in data.get('email', '') else data.get('username', '')
        password = data.get('password', '')
        
        print(f"🔐 Login attempt: {username}")
        
        # Verify credentials from database
        result = verify_user(username=username, password=password)
        
        if result['success']:
            user = result['user']
            
            # Update session
            manager.update_client_session(
                client_fd,
                authenticated=True,
                username=user['username'],
                user_id=user['_id']
            )
            
            # Send login result (0x1002 - LOGIN_RESULT)
            manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
                'success': True,
                'user_id': user['_id'],
                'username': user['username'],
                'fullname': user['fullname'],
                'rating': user['elo'],
                'wins': 0,  # Will be fetched from stats
                'losses': 0,
                'draws': 0
            })
        else:
            # Send login failure
            manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
                'success': False,
                'message': result['message']
            })
    
    
    # 0x0003 - GET_ONLINE_USERS: Lấy danh sách người chơi online
    def handle_get_online_users(client_fd: int, data: Dict):
        print(f"👥 Get online users request from fd={client_fd}")
        
        # Get current user session
        current_session = manager.client_sessions.get(client_fd, {})
        if not current_session.get('authenticated'):
            manager.send_to_client(client_fd, MessageTypeS2C.ONLINE_USERS_LIST, {
                'success': False,
                'users': []
            })
            return
        
        current_username = current_session.get('username')
        
        # Collect online users (exclude current user)
        online_users = []
        for fd, session in manager.client_sessions.items():
            if not session.get('authenticated'):
                continue
            
            username = session.get('username')
            if username == current_username:  # Skip current user
                continue
            
            # Check if user is in a game
            in_game = False
            for game_id, game_info in active_games.items():
                if game_info.get('is_ai_game'):
                    if game_info.get('player_fd') == fd:
                        in_game = True
                        break
                else:
                    if game_info.get('white_fd') == fd or game_info.get('black_fd') == fd:
                        in_game = True
                        break
            
            user_info = {
                'username': username,
                'fullname': session.get('fullname', username),
                'rating': session.get('rating', 1200),
                'status': 'in_game' if in_game else 'available'
            }
            online_users.append(user_info)
        
        print(f"   Found {len(online_users)} online users")
        
        # Send response
        manager.send_to_client(client_fd, MessageTypeS2C.ONLINE_USERS_LIST, {
            'success': True,
            'users': online_users
        })
    
    
    # 0x0010 - FIND_MATCH: Ghép cặp: Yêu cầu tìm trận (dựa trên ELO)
    def handle_find_match(client_fd: int, data: Dict):
        print(f"🔍 Find match request from fd={client_fd}")
        
        # Get user session
        session = manager.client_sessions.get(client_fd, {})
        if not session.get('authenticated'):
            return
        
        # Add to matchmaking queue
        matchmaking_queue.append(client_fd)
        
        # Match players if we have 2+ in queue
        if len(matchmaking_queue) >= 2:
            player1_fd = matchmaking_queue.pop(0)
            player2_fd = matchmaking_queue.pop(0)
            
            player1_session = manager.client_sessions.get(player1_fd, {})
            player2_session = manager.client_sessions.get(player2_fd, {})
            
            game_id = f'pvp_{int(time.time())}'
            
            # Create game in database
            game_result = create_game(
                game_id=game_id,
                white_player_id=player1_session.get('user_id'),
                black_player_id=player2_session.get('user_id'),
                white_username=player1_session.get('username', 'Player1'),
                black_username=player2_session.get('username', 'Player2'),
                time_control={'initial': 600, 'increment': 5}
            )
            
            if game_result['success']:
                active_games[game_id] = game_result['game']
                
                # Send to both players
                for fd, color in [(player1_fd, 'white'), (player2_fd, 'black')]:
                    opponent_session = player2_session if fd == player1_fd else player1_session
                    
                    manager.send_to_client(fd, MessageTypeS2C.MATCH_FOUND, {
                        'opponent_id': opponent_session.get('user_id'),
                        'opponent_username': opponent_session.get('username'),
                        'opponent_rating': 1500
                    })
                    
                    manager.send_to_client(fd, MessageTypeS2C.GAME_START, {
                        'game_id': game_id,
                        'color': color,
                        'opponent_color': 'black' if color == 'white' else 'white',
                        'opponent_username': opponent_session.get('username'),
                        'opponent_rating': 1500,
                        'time_control': {'initial': 600, 'increment': 5},
                        'fen': game_result['game']['fen']
                    })
    
    # 0x0011 - CANCEL_FIND_MATCH: Ghép cặp: Hủy yêu cầu tìm trận
    def handle_cancel_find_match(client_fd: int, data: Dict):
        print(f"❌ Cancel matchmaking from fd={client_fd}")
        
        if client_fd in matchmaking_queue:
            matchmaking_queue.remove(client_fd)
            print(f"✓ Removed from queue")
    
    # 0x0012 - FIND_AI_MATCH: Tính năng nâng cao: Yêu cầu đấu với AI (kèm tùy chỉnh)
    def handle_find_ai_match(client_fd: int, data: Dict):
        difficulty = data.get('difficulty', 'medium')
        color = data.get('color', 'white')
        
        print(f"🤖 AI match request from fd={client_fd}: difficulty={difficulty}, color={color}")
        
        # Get user session
        session = manager.client_sessions.get(client_fd, {})
        if not session.get('authenticated'):
            return
        
        game_id = f'ai_{client_fd}_{int(time.time())}'
        
        # Create AI game in database
        game_result = create_game(
            game_id=game_id,
            white_player_id=session.get('user_id') if color == 'white' else -1,
            black_player_id=session.get('user_id') if color == 'black' else -1,
            white_username=session.get('username', 'Player') if color == 'white' else f'AI Bot ({difficulty.capitalize()})',
            black_username=session.get('username', 'Player') if color == 'black' else f'AI Bot ({difficulty.capitalize()})',
            time_control={'initial': 600, 'increment': 5},
            is_ai_game=True,
            ai_difficulty=difficulty
        )
        
        if game_result['success']:
            active_games[game_id] = game_result['game']
            
            # Send game start notification (0x1101 - GAME_START)
            manager.send_to_client(client_fd, MessageTypeS2C.GAME_START, {
                'game_id': game_id,
                'opponent_username': f'AI Bot ({difficulty.capitalize()})',
                'opponent_id': -1,
                'opponent_rating': {'easy': 1000, 'medium': 1500, 'hard': 2000}.get(difficulty, 1500),
                'color': color,
                'opponent_color': 'black' if color == 'white' else 'white',
                'time_control': {'initial': 600, 'increment': 5},
                'fen': game_result['game']['fen']
            })
    
    # 0x0020 - MAKE_MOVE: Gameplay: Thực hiện một nước đi
    def handle_make_move(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        move = data.get('move', '')  # UCI format: e2e4
        
        print(f"♟️  Move from fd={client_fd}: {move} in game {game_id}")
        
        # Validate move with chess engine
        validation = validate_move(game_id, move)
        
        if validation['valid']:
            # Update game state in database
            update_game_state(game_id, move, validation['fen'])
            
            # Send game state update (0x1200 - GAME_STATE_UPDATE)
            manager.send_to_client(client_fd, MessageTypeS2C.GAME_STATE_UPDATE, {
                'game_id': game_id,
                'fen': validation['fen'],
                'last_move': move,
                'turn': 'black' if 'w' in validation['fen'] else 'white',
                'in_check': validation.get('in_check', False),
                'game_over': validation['game_over']
            })
            
            # If game over, end game and update ELO
            if validation['game_over']:
                end_game(game_id, validation['result'], 'completed')
                
                manager.send_to_client(client_fd, MessageTypeS2C.GAME_OVER, {
                    'game_id': game_id,
                    'result': validation['result'],
                    'reason': 'Checkmate' if 'win' in validation['result'] else 'Draw'
                })
        else:
            # Invalid move (0x1201 - INVALID_MOVE)
            manager.send_to_client(client_fd, MessageTypeS2C.INVALID_MOVE, {
                'reason': validation.get('reason', 'Invalid move')
            })
    
    # 0x0021 - RESIGN: Điều khiển trận: Xin đầu hàng
    def handle_resign(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        
        print(f"🏳️  Resign from fd={client_fd} in game {game_id}")
        
        # Get game info to determine winner
        game = get_game(game_id)
        if game:
            session = manager.client_sessions.get(client_fd, {})
            user_id = session.get('user_id')
            
            # Determine result based on who resigned
            if str(game['white_player_id']) == str(user_id):
                result = 'black_win'
            else:
                result = 'white_win'
            
            # End game in database
            end_game(game_id, result, 'resigned')
            
            # Send game over (0x1202 - GAME_OVER)
            manager.send_to_client(client_fd, MessageTypeS2C.GAME_OVER, {
                'game_id': game_id,
                'result': result,
                'winner': 'opponent',
                'reason': 'Player resigned'
            })
            
            # Cleanup
            if game_id in active_games:
                del active_games[game_id]
    
    # 0x0022 - OFFER_DRAW: Điều khiển trận: Đề nghị hòa
    def handle_offer_draw(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        
        print(f"🤝 Draw offer from fd={client_fd} in game {game_id}")
        
        # TODO: Forward to opponent
        # For now, just acknowledge (0x1203 - DRAW_OFFER_RECEIVED)
        manager.send_to_client(client_fd, MessageTypeS2C.DRAW_OFFER_RECEIVED, {
            'game_id': game_id,
            'message': 'Draw offer sent to opponent'
        })
    
    # 0x0023 - ACCEPT_DRAW: Điều khiển trận: Chấp nhận đề nghị hòa
    def handle_accept_draw(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        
        print(f"✅ Draw accepted from fd={client_fd} in game {game_id}")
        
        # End game with draw result
        end_game(game_id, 'draw', 'draw')
        
        # Send game over (0x1202 - GAME_OVER)
        manager.send_to_client(client_fd, MessageTypeS2C.GAME_OVER, {
            'game_id': game_id,
            'result': 'draw',
            'reason': 'Draw by agreement'
        })
        
        # Cleanup
        if game_id in active_games:
            del active_games[game_id]
    
    # 0x0024 - DECLINE_DRAW: Điều khiển trận: Từ chối đề nghị hòa
    def handle_decline_draw(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        
        print(f"❌ Draw declined from fd={client_fd} in game {game_id}")
        
        # Send notification (0x1204 - DRAW_OFFER_DECLINED)
        manager.send_to_client(client_fd, MessageTypeS2C.DRAW_OFFER_DECLINED, {
            'game_id': game_id,
            'message': 'Opponent declined draw offer'
        })
    
    # 0x0030 - GET_STATS: Hệ thống Xếp hạng: Yêu cầu xem thống kê (ELO, W/L/D)
    def handle_get_stats(client_fd: int, data: Dict):
        user_id = data.get('user_id', None)
        
        # If no user_id provided, use current session user
        if not user_id:
            session = manager.client_sessions.get(client_fd, {})
            user_id = session.get('user_id')
        
        print(f"📊 Stats request from fd={client_fd} for user {user_id}")
        
        # Get stats from database
        stats = get_user_stats(user_id)
        
        if stats:
            # Send stats response (0x1300 - STATS_RESPONSE)
            manager.send_to_client(client_fd, MessageTypeS2C.STATS_RESPONSE, stats)
        else:
            manager.send_to_client(client_fd, MessageTypeS2C.STATS_RESPONSE, {
                'error': 'User not found'
            })
    
    # 0x0031 - GET_HISTORY: Hệ thống Lịch sử: Yêu cầu xem lịch sử các ván đấu
    def handle_get_history(client_fd: int, data: Dict):
        print(f"📜 History request from fd={client_fd}")
        
        # Get user session
        session = manager.client_sessions.get(client_fd, {})
        user_id = session.get('user_id')
        
        if user_id:
            # Get game history from database
            history = get_user_game_history(user_id, limit=20)
            
            # Send history response (0x1301 - HISTORY_RESPONSE)
            manager.send_to_client(client_fd, MessageTypeS2C.HISTORY_RESPONSE, {
                'games': history
            })
        else:
            manager.send_to_client(client_fd, MessageTypeS2C.HISTORY_RESPONSE, {
                'games': [],
                'error': 'Not authenticated'
            })
    
    # 0x0032 - GET_REPLAY: Hệ thống Lịch sử: Yêu cầu dữ liệu xem lại (replay) 1 ván cụ thể
    def handle_get_replay(client_fd: int, data: Dict):
        game_id = data.get('game_id', '')
        
        print(f"🎬 Replay request from fd={client_fd} for game {game_id}")
        
        # Get game from database
        game = get_game(game_id)
        
        if game:
            # Generate PGN
            pgn = get_game_pgn(game_id)
            
            # Send replay data (0x1302 - REPLAY_DATA)
            manager.send_to_client(client_fd, MessageTypeS2C.REPLAY_DATA, {
                'game_id': game_id,
                'pgn': pgn if pgn else '',
                'moves': game['moves'],
                'white_player': game['white_username'],
                'black_player': game['black_username'],
                'result': game['result']
            })
        else:
            manager.send_to_client(client_fd, MessageTypeS2C.REPLAY_DATA, {
                'error': 'Game not found'
            })
    
    # Register all handlers
    manager.register_handler(MessageTypeC2S.REGISTER, handle_register)
    manager.register_handler(MessageTypeC2S.LOGIN, handle_login)
    manager.register_handler(MessageTypeC2S.GET_ONLINE_USERS, handle_get_online_users)
    manager.register_handler(MessageTypeC2S.FIND_MATCH, handle_find_match)
    manager.register_handler(MessageTypeC2S.CANCEL_FIND_MATCH, handle_cancel_find_match)
    manager.register_handler(MessageTypeC2S.FIND_AI_MATCH, handle_find_ai_match)
    manager.register_handler(MessageTypeC2S.MAKE_MOVE, handle_make_move)
    manager.register_handler(MessageTypeC2S.RESIGN, handle_resign)
    manager.register_handler(MessageTypeC2S.OFFER_DRAW, handle_offer_draw)
    manager.register_handler(MessageTypeC2S.ACCEPT_DRAW, handle_accept_draw)
    manager.register_handler(MessageTypeC2S.DECLINE_DRAW, handle_decline_draw)
    manager.register_handler(MessageTypeC2S.GET_STATS, handle_get_stats)
    manager.register_handler(MessageTypeC2S.GET_HISTORY, handle_get_history)
    manager.register_handler(MessageTypeC2S.GET_REPLAY, handle_get_replay)
    
    print("=" * 60)
    print("✓ All message handlers registered:")
    print(f"  Registered handlers: {list(manager.handlers.keys())}")
    print("  📝 0x0001 REGISTER - User registration")
    print("  🔐 0x0002 LOGIN - User login")
    print("  👥 0x0003 GET_ONLINE_USERS - Get online users")
    print("  🔍 0x0010 FIND_MATCH - Matchmaking")
    print("  ❌ 0x0011 CANCEL_FIND_MATCH - Cancel matchmaking")
    print("  🤖 0x0012 FIND_AI_MATCH - AI game")
    print("  ♟️  0x0020 MAKE_MOVE - Make a move")
    print("  🏳️  0x0021 RESIGN - Resign game")
    print("  🤝 0x0022 OFFER_DRAW - Offer draw")
    print("  ✅ 0x0023 ACCEPT_DRAW - Accept draw")
    print("  ❌ 0x0024 DECLINE_DRAW - Decline draw")
    print("  📊 0x0030 GET_STATS - Get user stats")
    print("  📜 0x0031 GET_HISTORY - Get game history")
    print("  🎬 0x0032 GET_REPLAY - Get game replay")
    print("=" * 60)
    
    # Import config for SERVER_PORT
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import SERVER_PORT
    
    # Start server
    if manager.start(port=SERVER_PORT):
        # Run event loop
        manager.run_forever()
