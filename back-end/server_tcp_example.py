"""
Example integration of TCP server with existing chess game logic
This file demonstrates how to integrate the new TCP server with your existing code
"""

import sys
import os

# Add tcp_server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tcp_server'))

from network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C
from database import Database
from engine import ChessEngine
import chess

class ChessServer:
    """
    Main chess server using TCP sockets instead of WebSockets
    """
    
    def __init__(self, port=8765):
        self.port = port
        self.network = NetworkManager()
        self.db = Database()
        
        # Game state management
        self.active_games = {}  # game_id -> {white_fd, black_fd, board, ...}
        self.matchmaking_queue = []  # List of client_fd waiting for match
        self.client_to_game = {}  # client_fd -> game_id
        
        # Register all message handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all message type handlers"""
        self.network.register_handler(MessageTypeC2S.REGISTER, self.handle_register)
        self.network.register_handler(MessageTypeC2S.LOGIN, self.handle_login)
        self.network.register_handler(MessageTypeC2S.FIND_MATCH, self.handle_find_match)
        self.network.register_handler(MessageTypeC2S.CANCEL_FIND_MATCH, self.handle_cancel_find_match)
        self.network.register_handler(MessageTypeC2S.FIND_AI_MATCH, self.handle_find_ai_match)
        self.network.register_handler(MessageTypeC2S.MAKE_MOVE, self.handle_make_move)
        self.network.register_handler(MessageTypeC2S.RESIGN, self.handle_resign)
        self.network.register_handler(MessageTypeC2S.OFFER_DRAW, self.handle_offer_draw)
        self.network.register_handler(MessageTypeC2S.ACCEPT_DRAW, self.handle_accept_draw)
        self.network.register_handler(MessageTypeC2S.DECLINE_DRAW, self.handle_decline_draw)
        self.network.register_handler(MessageTypeC2S.GET_STATS, self.handle_get_stats)
        self.network.register_handler(MessageTypeC2S.GET_HISTORY, self.handle_get_history)
    
    # ========== Authentication Handlers ==========
    
    def handle_register(self, client_fd: int, data: dict):
        """Handle user registration"""
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        
        # Validate input
        if not username or not password or not email:
            self.network.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
                'success': False,
                'error': 'Missing required fields'
            })
            return
        
        # Check if username exists
        if self.db.get_user_by_username(username):
            self.network.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
                'success': False,
                'error': 'Username already exists'
            })
            return
        
        # Create user
        user_id = self.db.create_user(username, password, email)
        if user_id:
            self.network.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
                'success': True,
                'message': 'Account created successfully',
                'user_id': user_id
            })
        else:
            self.network.send_to_client(client_fd, MessageTypeS2C.REGISTER_RESULT, {
                'success': False,
                'error': 'Failed to create account'
            })
    
    def handle_login(self, client_fd: int, data: dict):
        """Handle user login"""
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate credentials
        user = self.db.authenticate_user(username, password)
        
        if user:
            # Update session
            self.network.update_client_session(
                client_fd,
                authenticated=True,
                username=user['username'],
                user_id=user['id'],
                state=2  # CLIENT_AUTHENTICATED
            )
            
            # Send success response
            self.network.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
                'success': True,
                'user_id': user['id'],
                'username': user['username'],
                'rating': user.get('rating', 1500),
                'wins': user.get('wins', 0),
                'losses': user.get('losses', 0),
                'draws': user.get('draws', 0)
            })
            
            print(f"✓ User logged in: {username} (fd={client_fd})")
        else:
            self.network.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
                'success': False,
                'error': 'Invalid username or password'
            })
    
    # ========== Matchmaking Handlers ==========
    
    def handle_find_match(self, client_fd: int, data: dict):
        """Handle matchmaking request"""
        session = self.network.get_client_info(client_fd)
        if not session or not session.get('authenticated'):
            return
        
        # Check if already in queue or game
        if client_fd in self.matchmaking_queue:
            return
        if client_fd in self.client_to_game:
            return
        
        # Add to queue
        self.matchmaking_queue.append(client_fd)
        print(f"Player {session['username']} added to matchmaking queue")
        
        # Try to match with someone
        self._try_matchmaking()
    
    def handle_cancel_find_match(self, client_fd: int, data: dict):
        """Handle cancel matchmaking"""
        if client_fd in self.matchmaking_queue:
            self.matchmaking_queue.remove(client_fd)
            print(f"Player removed from matchmaking queue (fd={client_fd})")
    
    def handle_find_ai_match(self, client_fd: int, data: dict):
        """Handle AI match request"""
        session = self.network.get_client_info(client_fd)
        if not session or not session.get('authenticated'):
            return
        
        difficulty = data.get('difficulty', 'medium')
        
        # Create AI game
        game_id = f"ai_{client_fd}_{os.urandom(4).hex()}"
        board = chess.Board()
        
        self.active_games[game_id] = {
            'white_fd': client_fd,
            'black_fd': None,  # AI player
            'board': board,
            'white_player': session['username'],
            'black_player': 'AI',
            'is_ai_game': True,
            'ai_difficulty': difficulty,
            'current_turn': 'white'
        }
        
        self.client_to_game[client_fd] = game_id
        
        # Notify player
        self.network.send_to_client(client_fd, MessageTypeS2C.GAME_START, {
            'game_id': game_id,
            'color': 'white',
            'opponent': 'AI',
            'opponent_rating': 1500,
            'fen': board.fen()
        })
        
        print(f"AI game started: {game_id}")
    
    def _try_matchmaking(self):
        """Try to match players in queue"""
        if len(self.matchmaking_queue) < 2:
            return
        
        # Take first two players
        player1_fd = self.matchmaking_queue.pop(0)
        player2_fd = self.matchmaking_queue.pop(0)
        
        session1 = self.network.get_client_info(player1_fd)
        session2 = self.network.get_client_info(player2_fd)
        
        if not session1 or not session2:
            return
        
        # Create game
        game_id = f"game_{os.urandom(8).hex()}"
        board = chess.Board()
        
        self.active_games[game_id] = {
            'white_fd': player1_fd,
            'black_fd': player2_fd,
            'board': board,
            'white_player': session1['username'],
            'black_player': session2['username'],
            'is_ai_game': False,
            'current_turn': 'white'
        }
        
        self.client_to_game[player1_fd] = game_id
        self.client_to_game[player2_fd] = game_id
        
        # Notify both players
        self.network.send_to_client(player1_fd, MessageTypeS2C.GAME_START, {
            'game_id': game_id,
            'color': 'white',
            'opponent': session2['username'],
            'opponent_rating': session2.get('rating', 1500),
            'fen': board.fen()
        })
        
        self.network.send_to_client(player2_fd, MessageTypeS2C.GAME_START, {
            'game_id': game_id,
            'color': 'black',
            'opponent': session1['username'],
            'opponent_rating': session1.get('rating', 1500),
            'fen': board.fen()
        })
        
        print(f"Match created: {session1['username']} vs {session2['username']} ({game_id})")
    
    # ========== Game Handlers ==========
    
    def handle_make_move(self, client_fd: int, data: dict):
        """Handle chess move"""
        game_id = self.client_to_game.get(client_fd)
        if not game_id:
            return
        
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Validate it's player's turn
        is_white = (client_fd == game['white_fd'])
        if (is_white and game['current_turn'] != 'white') or \
           (not is_white and game['current_turn'] != 'black'):
            self.network.send_to_client(client_fd, MessageTypeS2C.INVALID_MOVE, {
                'error': 'Not your turn'
            })
            return
        
        # Parse move
        from_square = data.get('from')
        to_square = data.get('to')
        promotion = data.get('promotion')
        
        try:
            # Create move
            move = chess.Move.from_uci(f"{from_square}{to_square}{promotion or ''}")
            
            # Validate and make move
            if move in game['board'].legal_moves:
                game['board'].push(move)
                game['current_turn'] = 'black' if is_white else 'white'
                
                # Check game state
                game_over = game['board'].is_game_over()
                
                # Prepare update
                update_data = {
                    'game_id': game_id,
                    'fen': game['board'].fen(),
                    'move': {
                        'from': from_square,
                        'to': to_square,
                        'promotion': promotion
                    },
                    'is_check': game['board'].is_check(),
                    'game_over': game_over
                }
                
                if game_over:
                    if game['board'].is_checkmate():
                        winner = 'white' if not is_white else 'black'
                        update_data['result'] = 'checkmate'
                        update_data['winner'] = winner
                    elif game['board'].is_stalemate():
                        update_data['result'] = 'stalemate'
                    elif game['board'].is_insufficient_material():
                        update_data['result'] = 'insufficient_material'
                
                # Send to both players
                self.network.send_to_client(client_fd, MessageTypeS2C.GAME_STATE_UPDATE, update_data)
                
                opponent_fd = game['black_fd'] if is_white else game['white_fd']
                if opponent_fd:
                    self.network.send_to_client(opponent_fd, MessageTypeS2C.GAME_STATE_UPDATE, update_data)
                
                # Handle AI response
                if game.get('is_ai_game') and not game_over:
                    self._make_ai_move(game_id)
            
            else:
                self.network.send_to_client(client_fd, MessageTypeS2C.INVALID_MOVE, {
                    'error': 'Illegal move'
                })
        
        except Exception as e:
            self.network.send_to_client(client_fd, MessageTypeS2C.INVALID_MOVE, {
                'error': str(e)
            })
    
    def handle_resign(self, client_fd: int, data: dict):
        """Handle resignation"""
        game_id = self.client_to_game.get(client_fd)
        if not game_id:
            return
        
        game = self.active_games.get(game_id)
        if not game:
            return
        
        is_white = (client_fd == game['white_fd'])
        winner = 'black' if is_white else 'white'
        
        # Notify both players
        game_over_data = {
            'game_id': game_id,
            'result': 'resignation',
            'winner': winner
        }
        
        self.network.send_to_client(client_fd, MessageTypeS2C.GAME_OVER, game_over_data)
        
        opponent_fd = game['black_fd'] if is_white else game['white_fd']
        if opponent_fd:
            self.network.send_to_client(opponent_fd, MessageTypeS2C.GAME_OVER, game_over_data)
        
        # Cleanup
        self._cleanup_game(game_id)
    
    def handle_offer_draw(self, client_fd: int, data: dict):
        """Handle draw offer"""
        game_id = self.client_to_game.get(client_fd)
        if not game_id:
            return
        
        game = self.active_games.get(game_id)
        if not game:
            return
        
        is_white = (client_fd == game['white_fd'])
        opponent_fd = game['black_fd'] if is_white else game['white_fd']
        
        if opponent_fd:
            self.network.send_to_client(opponent_fd, MessageTypeS2C.DRAW_OFFER_RECEIVED, {
                'game_id': game_id
            })
    
    def handle_accept_draw(self, client_fd: int, data: dict):
        """Handle draw acceptance"""
        game_id = self.client_to_game.get(client_fd)
        if not game_id:
            return
        
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Notify both players
        game_over_data = {
            'game_id': game_id,
            'result': 'draw_agreement',
            'winner': None
        }
        
        self.network.send_to_client(game['white_fd'], MessageTypeS2C.GAME_OVER, game_over_data)
        if game['black_fd']:
            self.network.send_to_client(game['black_fd'], MessageTypeS2C.GAME_OVER, game_over_data)
        
        # Cleanup
        self._cleanup_game(game_id)
    
    def handle_decline_draw(self, client_fd: int, data: dict):
        """Handle draw decline"""
        game_id = self.client_to_game.get(client_fd)
        if not game_id:
            return
        
        game = self.active_games.get(game_id)
        if not game:
            return
        
        is_white = (client_fd == game['white_fd'])
        opponent_fd = game['black_fd'] if is_white else game['white_fd']
        
        if opponent_fd:
            self.network.send_to_client(opponent_fd, MessageTypeS2C.DRAW_OFFER_DECLINED, {
                'game_id': game_id
            })
    
    # ========== Stats Handlers ==========
    
    def handle_get_stats(self, client_fd: int, data: dict):
        """Handle stats request"""
        session = self.network.get_client_info(client_fd)
        if not session or not session.get('authenticated'):
            return
        
        # Get user stats from database
        stats = self.db.get_user_stats(session['user_id'])
        
        self.network.send_to_client(client_fd, MessageTypeS2C.STATS_RESPONSE, stats)
    
    def handle_get_history(self, client_fd: int, data: dict):
        """Handle history request"""
        session = self.network.get_client_info(client_fd)
        if not session or not session.get('authenticated'):
            return
        
        # Get game history
        history = self.db.get_user_history(session['user_id'])
        
        self.network.send_to_client(client_fd, MessageTypeS2C.HISTORY_RESPONSE, {
            'games': history
        })
    
    # ========== Helper Methods ==========
    
    def _make_ai_move(self, game_id: str):
        """Make AI move"""
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Use chess engine to get best move
        engine = ChessEngine(game['board'])
        ai_move = engine.get_best_move(difficulty=game.get('ai_difficulty', 'medium'))
        
        if ai_move:
            game['board'].push(ai_move)
            game['current_turn'] = 'white'
            
            # Send update to player
            self.network.send_to_client(game['white_fd'], MessageTypeS2C.GAME_STATE_UPDATE, {
                'game_id': game_id,
                'fen': game['board'].fen(),
                'move': {
                    'from': chess.square_name(ai_move.from_square),
                    'to': chess.square_name(ai_move.to_square),
                    'promotion': None
                },
                'is_check': game['board'].is_check(),
                'game_over': game['board'].is_game_over()
            })
    
    def _cleanup_game(self, game_id: str):
        """Clean up finished game"""
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Remove from tracking
        if game['white_fd'] in self.client_to_game:
            del self.client_to_game[game['white_fd']]
        if game['black_fd'] and game['black_fd'] in self.client_to_game:
            del self.client_to_game[game['black_fd']]
        
        del self.active_games[game_id]
        print(f"Game cleaned up: {game_id}")
    
    # ========== Main Loop ==========
    
    def run(self):
        """Start and run the server"""
        if not self.network.start(self.port):
            print("Failed to start server")
            return
        
        print(f"Chess server running on port {self.port}")
        
        try:
            self.network.run_forever(poll_timeout_ms=100)
        except KeyboardInterrupt:
            print("\nServer interrupted")
        finally:
            print("Shutting down...")


if __name__ == '__main__':
    server = ChessServer(port=8765)
    server.run()
