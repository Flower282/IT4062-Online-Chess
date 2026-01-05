"""
Game Handler
Xử lý logic game (moves, resign, draw)
"""

import chess
import random
import time
from services.game_service import (
    get_game, update_game_state, end_game, validate_move
)
from .win_handler import WinHandler
from minimax.search import search as minimax_search


class GameHandler:
    """Handler cho game logic (make move, resign, draw offers)"""
    
    # Timeout for PvP moves (in seconds)
    MOVE_TIMEOUT = 60
    
    def __init__(self, network_manager, matchmaking_handler, model=None):
        """
        Args:
            network_manager: Instance của NetworkManager
            matchmaking_handler: Instance của MatchmakingHandler (để access active_games)
            model: ML Model for AI
        """
        self.network = network_manager
        self.matchmaking = matchmaking_handler
        self.model = model
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
            
            # Update last move time in active_games
            if game_id in self.matchmaking.active_games:
                self.matchmaking.active_games[game_id]['last_move_time'] = time.time()
            
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
        Tạo nước đi cho AI dựa trên độ khó
        """
        try:
            # Get current board state
            board = chess.Board(current_fen)
            difficulty = game_info.get('game', {}).get('ai_difficulty', 'medium')
            
            print(f"🤖 AI thinking ({difficulty})...")
            
            ai_move = None
            
            # --- Easy Mode: Random Move ---
            if difficulty == 'easy':
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    ai_move = random.choice(legal_moves)

            # --- Medium/Hard Mode: Minimax ---
            else:
                # Set parameters based on difficulty
                depth = 2 if difficulty == 'medium' else 3
                use_ml = (difficulty == 'hard' and self.model is not None)
                
                # Minimax Search
                # Note: 'is_ai_white' depends on AI color in game_info
                # game_info['player_color'] is the HUMAN's color
                is_ai_white = (game_info.get('player_color') != 'white')
                
                best_value = -99999
                alpha = -100000
                beta = 100000
                best_move = None
                
                # Get moves (ML-ordered or standard)
                if use_ml:
                    # Import here to avoid circular dependency if possible, or assume global import
                    from ml.filter import filter_good_moves
                    moves_with_prob = filter_good_moves(board=board, classifier=self.model, first_print=False)
                    # moves_with_prob is list of [move, prob]
                    # We just need the moves for the loop
                    moves = [m[0] for m in moves_with_prob]
                    # Fallback if filter returns empty/few
                    if len(moves) < 5:
                        remaining = [m for m in board.legal_moves if m not in moves]
                        moves.extend(remaining)
                else:
                    moves = list(board.legal_moves)
                
                # Root search loop
                for move in moves:
                    board.push(move)
                    # Minimize for opponent
                    value = -minimax_search(depth - 1, -beta, -alpha, board, is_ai_white, use_ml, self.model)
                    board.pop()
                    
                    if value > best_value:
                        best_value = value
                        best_move = move
                    alpha = max(alpha, value)
                
                ai_move = best_move

            # Fallback to random if AI failed to find a move
            if not ai_move:
                 legal_moves = list(board.legal_moves)
                 if legal_moves:
                    ai_move = random.choice(legal_moves)
            
            if not ai_move:
                print("⚠ AI has no legal moves (Checkmate/Stalemate should have been caught)")
                return

            ai_move_uci = ai_move.uci()
            print(f"AI move: {ai_move_uci} in game {game_id}")
            
            # Validate and apply AI move
            validation = validate_move(game_id, ai_move_uci)
            
            if validation['valid']:
                # Update game state (DB + Memory)
                update_game_state(game_id, ai_move_uci, validation['fen'])
                if game_id in self.matchmaking.active_games:
                    self.matchmaking.active_games[game_id]['last_move_time'] = time.time()
                
                # Send game state to player
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
                
                # Check End Game
                if validation['game_over']:
                    end_game(game_id, validation['result'], 'completed')
                    reason = 'Checkmate' if 'win' in validation['result'] else 'Draw'
                    self.win_handler.broadcast_game_over(game_id, validation['result'], reason, game_info)
        
        except Exception as e:
            print(f"AI move error: {e}")
            import traceback
            traceback.print_exc()

    def check_timeouts(self):
        """
        Check for PvP games where a player has exceeded the move time limit.
        If timeout, make a random move for them.
        """
        current_time = time.time()
        timeout_games = []
        
        # Identify games to process (avoid modifying dict while iterating)
        for game_id, info in self.matchmaking.active_games.items():
            if info.get('is_ai_game'):
                continue
                
            last_move_time = info.get('last_move_time')
            if not last_move_time:
                # Initialize if missing (e.g. game just started)
                info['last_move_time'] = current_time
                continue
                
            if current_time - last_move_time > self.MOVE_TIMEOUT:
                timeout_games.append((game_id, info))
        
        # Process timeouts
        for game_id, info in timeout_games:
            print(f"Timeout in game {game_id}. Forcing random move.")
            
            try:
                # Get current FEN to determine turn
                game = get_game(game_id)
                if not game or game['status'] != 'active':
                    continue
                    
                fen = game['fen']
                board = chess.Board(fen)
                
                # Determine whose turn it is
                turn_color = 'white' if board.turn == chess.WHITE else 'black'
                
                # Make random legal move
                legal_moves = list(board.legal_moves)
                if not legal_moves:
                    continue
                    
                random_move = random.choice(legal_moves)
                move_uci = random_move.uci()
                
                print(f"Random move for {turn_color}: {move_uci}")
                
                # Reuse handle_make_move logic effectively by simulating the call or calling core logic
                # We need to broadcast to both.
                
                # Validate & Apply
                validation = validate_move(game_id, move_uci)
                if validation['valid']:
                    update_game_state(game_id, move_uci, validation['fen'])
                    info['last_move_time'] = time.time() # Reset timer
                    
                    # Broadcast update
                    msg = {
                        'game_id': game_id,
                        'fen': validation['fen'],
                        'last_move': move_uci,
                        'turn': 'black' if 'w' in validation['fen'] else 'white',
                        'in_check': validation.get('in_check', False),
                        'game_over': validation['game_over'],
                        'message': f'Time expired for {turn_color}. Random move made.'
                    }
                    
                    white_fd = info.get('white_fd')
                    black_fd = info.get('black_fd')
                    
                    if white_fd and white_fd != -1:
                        self.network.send_to_client(white_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, msg)
                    if black_fd and black_fd != -1:
                        self.network.send_to_client(black_fd, self.MessageTypeS2C.GAME_STATE_UPDATE, msg)
                        
                    # Handle Game Over
                    if validation['game_over']:
                        end_game(game_id, validation['result'], 'completed')
                        reason = 'Checkmate' if 'win' in validation['result'] else 'Draw'
                        self.win_handler.broadcast_game_over(game_id, validation['result'], reason, info)
                        
            except Exception as e:
                print(f"Error handling timeout for game {game_id}: {e}")
    
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
        
        print(f"Draw offer from fd={client_fd} in game {game_id}")
        
        # Find opponent and forward the draw offer
        game_info = self.matchmaking.active_games.get(game_id)
        if game_info and not game_info.get('is_ai_game'):
            white_fd = game_info.get('white_fd')
            black_fd = game_info.get('black_fd')
            
            # Determine opponent
            opponent_fd = black_fd if client_fd == white_fd else white_fd
            
            if opponent_fd and opponent_fd != -1:
                # Send draw offer to opponent
                self.network.send_to_client(opponent_fd, self.MessageTypeS2C.DRAW_OFFER_RECEIVED, {
                    'game_id': game_id,
                    'message': 'Opponent offered a draw'
                })
                
                # Acknowledge to sender
                self.network.send_to_client(client_fd, self.MessageTypeS2C.DRAW_OFFER_RECEIVED, {
                    'game_id': game_id,
                    'message': 'Draw offer sent to opponent'
                })
        else:
            # Fallback acknowledgment
            self.network.send_to_client(client_fd, self.MessageTypeS2C.DRAW_OFFER_RECEIVED, {
                'game_id': game_id,
                'message': 'Draw offer sent to opponent'
            })
    
    def handle_accept_draw(self, client_fd: int, data: dict):
        """
        0x0023 - ACCEPT_DRAW: Điều khiển trận: Chấp nhận đề nghị hòa
        """
        game_id = data.get('game_id', '')
        
        print(f"Draw accepted from fd={client_fd} in game {game_id}")
        
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
        
        print(f"Draw declined from fd={client_fd} in game {game_id}")
        
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
        
        # Acknowledge to decliner
        self.network.send_to_client(client_fd, self.MessageTypeS2C.DRAW_OFFER_DECLINED, {
            'game_id': game_id,
            'message': 'Draw offer declined'
        })
