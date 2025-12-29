"""
Matchmaking Handler
Xử lý tìm trận và ghép cặp
"""

import time
from services.game_service import create_game


class MatchmakingHandler:
    """Handler cho matchmaking (find match, AI match)"""
    
    def __init__(self, network_manager):
        """
        Args:
            network_manager: Instance của NetworkManager
        """
        self.network = network_manager
        self.MessageTypeS2C = None  # Will be set by server
        
        # Matchmaking state
        self.matchmaking_queue = []
        self.active_games = {}
    
    def handle_find_match(self, client_fd: int, data: dict):
        """
        0x0010 - FIND_MATCH: Ghép cặp: Yêu cầu tìm trận (dựa trên ELO)
        """
        print(f"🔍 Find match request from fd={client_fd}")
        
        # Get user session
        session = self.network.client_sessions.get(client_fd, {})
        if not session.get('authenticated'):
            return
        
        # Add to matchmaking queue
        self.matchmaking_queue.append(client_fd)
        
        # Match players if we have 2+ in queue
        if len(self.matchmaking_queue) >= 2:
            player1_fd = self.matchmaking_queue.pop(0)
            player2_fd = self.matchmaking_queue.pop(0)
            
            player1_session = self.network.client_sessions.get(player1_fd, {})
            player2_session = self.network.client_sessions.get(player2_fd, {})
            
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
                # Store game with player file descriptors for broadcasting
                self.active_games[game_id] = {
                    'game': game_result['game'],
                    'white_fd': player1_fd,
                    'black_fd': player2_fd,
                    'is_ai_game': False
                }
                
                # Send to both players
                for fd, color in [(player1_fd, 'white'), (player2_fd, 'black')]:
                    opponent_session = player2_session if fd == player1_fd else player1_session
                    
                    self.network.send_to_client(fd, self.MessageTypeS2C.MATCH_FOUND, {
                        'opponent_id': opponent_session.get('user_id'),
                        'opponent_username': opponent_session.get('username'),
                        'opponent_rating': 1500
                    })
                    
                    self.network.send_to_client(fd, self.MessageTypeS2C.GAME_START, {
                        'game_id': game_id,
                        'color': color,
                        'opponent_color': 'black' if color == 'white' else 'white',
                        'opponent_username': opponent_session.get('username'),
                        'opponent_rating': 1500,
                        'time_control': {'initial': 600, 'increment': 5},
                        'fen': game_result['game']['fen']
                    })
    
    def handle_cancel_find_match(self, client_fd: int, data: dict):
        """
        0x0011 - CANCEL_FIND_MATCH: Ghép cặp: Hủy yêu cầu tìm trận
        """
        print(f"❌ Cancel matchmaking from fd={client_fd}")
        
        if client_fd in self.matchmaking_queue:
            self.matchmaking_queue.remove(client_fd)
            print(f"✓ Removed from queue")
    
    def handle_find_ai_match(self, client_fd: int, data: dict):
        """
        0x0012 - FIND_AI_MATCH: Tính năng nâng cao: Yêu cầu đấu với AI (kèm tùy chỉnh)
        """
        difficulty = data.get('difficulty', 'medium')
        color = data.get('color', 'white')
        
        print(f"🤖 AI match request from fd={client_fd}: difficulty={difficulty}, color={color}")
        
        # Get user session
        session = self.network.client_sessions.get(client_fd, {})
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
            # Store AI game with player file descriptor
            self.active_games[game_id] = {
                'game': game_result['game'],
                'white_fd': client_fd if color == 'white' else -1,
                'black_fd': client_fd if color == 'black' else -1,
                'is_ai_game': True,
                'player_fd': client_fd,
                'player_color': color
            }
            
            # Send game start notification (0x1101 - GAME_START)
            self.network.send_to_client(client_fd, self.MessageTypeS2C.GAME_START, {
                'game_id': game_id,
                'opponent_username': f'AI Bot ({difficulty.capitalize()})',
                'opponent_id': -1,
                'opponent_rating': {'easy': 1000, 'medium': 1500, 'hard': 2000}.get(difficulty, 1500),
                'color': color,
                'opponent_color': 'black' if color == 'white' else 'white',
                'time_control': {'initial': 600, 'increment': 5},
                'fen': game_result['game']['fen']
            })
