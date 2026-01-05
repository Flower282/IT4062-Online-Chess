"""
Game Handler
Xử lý logic game (moves, resign, draw)
"""

import chess
import random
from services.game_service import (
    get_game, update_game_state, end_game, validate_move
)
from .win_handler import WinHandler


class GameHandler:
    """Handler cho game logic (make move, resign, draw offers)"""
    
    def __init__(self, network_manager, matchmaking_handler):
        """
        Args:
            network_manager: Instance của NetworkManager
            matchmaking_handler: Instance của MatchmakingHandler (để access active_games)
        """
        self.network = network_manager
        self.matchmaking = matchmaking_handler
        self.win_handler = WinHandler(network_manager)
        self.MessageTypeS2C = None  # Will be set by server
    
    def handle_make_move(self, client_fd: int, data: dict):
        """
        0x0020 - MAKE_MOVE: Gameplay: Thực hiện một nước đi
        """
        game_id = data.get('game_id', '')
        move = data.get('move', '')  # UCI format: e2e4
        
        print(f"♟️  Move from fd={client_fd}: {move} in game {game_id}")
        
        # Validate move with chess engine
        validation = validate_move(game_id, move)
        
        if validation['valid']:
            # Update game state in database
            update_game_state(game_id, move, validation['fen'])
            
            # Get game info to broadcast to both players
            game_info = self.matchmaking.active_games.get(game_id)
            
            # Prepare game state update message
            game_state_msg = {
                'game_id': game_id,
                'fen': validation['fen'],
                'last_move': move,
                'turn': 'black' if 'w' in validation['fen'] else 'white',
                'in_check': validation.get('in_check', False),
                'game_over': validation['game_over']
            }
            
            # Broadcast to both players (or just player for AI games)
            if game_info:
                if game_info.get('is_ai_game'):
                    # Send state update to human player
                    player_fd = game_info.get('player_fd')
                    if player_fd and player_fd != -1:
                        self.network.send_to_client(player_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, game_state_msg)
                    
                    # AI game: trigger AI move if game not over
                    if not validation['game_over']:
                        self._make_ai_move(game_id, game_info, validation['fen'])
                else:
                    # Send to both players in PvP game
                    white_fd = game_info.get('white_fd')
                    black_fd = game_info.get('black_fd')
                    
                    if white_fd and white_fd != -1:
                        self.network.send_to_client(white_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, game_state_msg)
                    if black_fd and black_fd != -1:
                        self.network.send_to_client(black_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, game_state_msg)
            else:
                # Fallback: send only to current player if game not in active_games
                self.network.send_to_client(client_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, game_state_msg)
            
            # If game over, end game and update ELO
            if validation['game_over']:
                end_game(game_id, validation['result'], 'completed')
                
                # Broadcast personalized game over messages
                reason = 'Checkmate' if 'win' in validation['result'] else 'Draw'
                if game_info:
                    self.win_handler.broadcast_game_over(game_id, validation['result'], reason, game_info)
        else:
            # Invalid move (0x1201 - INVALID_MOVE)
            self.network.send_to_client(client_fd, self.MessageTypeS2C.INVALID_MOVE, {
                'reason': validation.get('reason', 'Invalid move')
            })
    
    def _make_ai_move(self, game_id: str, game_info: dict, current_fen: str):
        """
        Tạo nước đi cho AI và gửi về player
        
        Args:
            game_id: ID của game
            game_info: Thông tin game
            current_fen: FEN hiện tại sau khi player đi
        """
        try:
            # Get current board state
            board = chess.Board(current_fen)
            
            # Simple random AI - chọn random một nước đi hợp lệ
            legal_moves = list(board.legal_moves)
            if not legal_moves:
                return
            
            ai_move = random.choice(legal_moves)
            ai_move_uci = ai_move.uci()
            
            print(f"🤖 AI move: {ai_move_uci} in game {game_id}")
            
            # Validate and apply AI move
            validation = validate_move(game_id, ai_move_uci)
            
            if validation['valid']:
                # Update game state in database
                update_game_state(game_id, ai_move_uci, validation['fen'])
                
                # Send game state update to player
                player_fd = game_info.get('player_fd')
                if player_fd and player_fd != -1:
                    self.network.send_to_client(player_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, {
                        'game_id': game_id,
                        'fen': validation['fen'],
                        'last_move': ai_move_uci,
                        'turn': 'black' if 'w' in validation['fen'] else 'white',
                        'in_check': validation.get('in_check', False),
                        'game_over': validation['game_over']
                    })
                
                # Check if AI move ended the game
                if validation['game_over']:
                    end_game(game_id, validation['result'], 'completed')
                    
                    # Broadcast game over
                    reason = 'Checkmate' if 'win' in validation['result'] else 'Draw'
                    self.win_handler.broadcast_game_over(game_id, validation['result'], reason, game_info)
        
        except Exception as e:
            print(f"❌ AI move error: {e}")
    
    def handle_resign(self, client_fd: int, data: dict):
        """
        0x0021 - RESIGN: Điều khiển trận: Xin đầu hàng
        """
        game_id = data.get('game_id', '')
        
        print(f"🏳️  Resign from fd={client_fd} in game {game_id}")
        
        # Get game info to determine winner
        game = get_game(game_id)
        if game:
            session = self.network.client_sessions.get(client_fd, {})
            user_id = session.get('user_id')
            
            # Determine result based on who resigned
            if str(game['white_player_id']) == str(user_id):
                result = 'black_win'
            else:
                result = 'white_win'
            
            # End game in database
            end_game(game_id, result, 'resigned')
            
            # Broadcast personalized game over messages
            game_info = self.matchmaking.active_games.get(game_id)
            if game_info:
                self.win_handler.broadcast_game_over(game_id, result, 'Player resigned', game_info)
            
            # Cleanup
            if game_id in self.matchmaking.active_games:
                del self.matchmaking.active_games[game_id]
    
    def handle_offer_draw(self, client_fd: int, data: dict):
        """
        0x0022 - OFFER_DRAW: Điều khiển trận: Đề nghị hòa
        """
        game_id = data.get('game_id', '')
        
        print(f"🤝 Draw offer from fd={client_fd} in game {game_id}")
        
        # Find opponent and forward the draw offer
        game_info = self.matchmaking.active_games.get(game_id)
        if game_info and not game_info.get('is_ai_game'):
            white_fd = game_info.get('white_fd')
            black_fd = game_info.get('black_fd')
            
            # Determine opponent
            opponent_fd = black_fd if client_fd == white_fd else white_fd
            
            if opponent_fd and opponent_fd != -1:
                # Send draw offer to opponent only
                self.network.send_to_client(opponent_fd, self.MessageTypeS2C.DRAW_OFFER_RECEIVED, {
                    'game_id': game_id,
                    'message': 'Opponent offered a draw'
                })
                print(f"✓ Draw offer sent to opponent (fd={opponent_fd})")
        else:
            print(f"⚠ Game {game_id} not found or is AI game")
    
    def handle_accept_draw(self, client_fd: int, data: dict):
        """
        0x0023 - ACCEPT_DRAW: Điều khiển trận: Chấp nhận đề nghị hòa
        """
        game_id = data.get('game_id', '')
        
        print(f"✅ Draw accepted from fd={client_fd} in game {game_id}")
        
        # End game with draw result
        end_game(game_id, 'draw', 'draw')
        
        # Broadcast personalized game over messages
        game_info = self.matchmaking.active_games.get(game_id)
        if game_info:
            self.win_handler.broadcast_game_over(game_id, 'draw', 'Draw by agreement', game_info)
        
        # Cleanup
        if game_id in self.matchmaking.active_games:
            del self.matchmaking.active_games[game_id]
    
    def handle_decline_draw(self, client_fd: int, data: dict):
        """
        0x0024 - DECLINE_DRAW: Điều khiển trận: Từ chối đề nghị hòa
        """
        game_id = data.get('game_id', '')
        
        print(f"❌ Draw declined from fd={client_fd} in game {game_id}")
        
        # Find opponent and notify them
        game_info = self.matchmaking.active_games.get(game_id)
        if game_info and not game_info.get('is_ai_game'):
            white_fd = game_info.get('white_fd')
            black_fd = game_info.get('black_fd')
            
            # Determine opponent (the one who offered the draw)
            opponent_fd = black_fd if client_fd == white_fd else white_fd
            
            if opponent_fd and opponent_fd != -1:
                # Notify opponent that draw was declined
                self.network.send_to_client(opponent_fd, self.MessageTypeS2C.DRAW_OFFER_DECLINED, {
                    'game_id': game_id,
                    'message': 'Opponent declined draw offer'
                })
                print(f"✓ Draw decline notification sent to opponent (fd={opponent_fd})")
        else:
            print(f"⚠ Game {game_id} not found or is AI game")
