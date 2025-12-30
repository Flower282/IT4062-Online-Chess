"""
Win Handler
Xử lý logic hiển thị kết quả game (you win, you loss, draw) cho từng người chơi
"""


class WinHandler:
    """Handler cho việc broadcast personalized game over messages"""
    
    def __init__(self, network_manager):
        """
        Args:
            network_manager: Instance của NetworkManager
        """
        self.network = network_manager
        self.MessageTypeS2C = None  # Will be set by server
    
    def broadcast_game_over(self, game_id: str, result: str, reason: str, game_info: dict):
        """
        Broadcast game over với personalized messages cho từng người chơi
        
        Args:
            game_id: ID của game
            result: 'white_win', 'black_win', hoặc 'draw'
            reason: Lý do kết thúc (Checkmate, Resign, Draw by agreement...)
            game_info: Thông tin game từ active_games với các keys:
                - is_ai_game: bool
                - player_fd: int (nếu AI game)
                - player_color: str (nếu AI game)
                - white_fd: int (nếu PvP game)
                - black_fd: int (nếu PvP game)
        """
        if not game_info:
            return
        
        if game_info.get('is_ai_game'):
            # AI game - chỉ gửi cho người chơi
            self._send_ai_game_result(game_id, result, reason, game_info)
        else:
            # PvP game - gửi personalized message cho mỗi người
            self._send_pvp_game_result(game_id, result, reason, game_info)
    
    def _send_ai_game_result(self, game_id: str, result: str, reason: str, game_info: dict):
        """
        Gửi kết quả game cho AI game
        
        Args:
            game_id: ID của game
            result: Kết quả game
            reason: Lý do kết thúc
            game_info: Thông tin game
        """
        player_fd = game_info.get('player_fd')
        player_color = game_info.get('player_color')
        
        if not player_fd or player_fd == -1:
            return
        
        print(f"🎮 AI Game Result - game_id: {game_id}, result: {result}, player_color: {player_color}, reason: {reason}")
        
        # Xác định người chơi thắng hay thua
        if result == 'draw':
            outcome = 'draw'
            message = 'Game ended in a draw'
        elif (result == 'white_win' and player_color == 'white') or \
             (result == 'black_win' and player_color == 'black'):
            outcome = 'you_win'
            message = f'You Win! {reason}'
        else:
            outcome = 'you_loss'
            message = f'You Lost! {reason}'
        
        print(f"   → Outcome: {outcome}, Message: {message}")
        
        self.network.send_to_client(player_fd, self.MessageTypeS2C.GAME_OVER, {
            'game_id': game_id,
            'result': result,
            'outcome': outcome,
            'message': message,
            'reason': reason
        })
    
    def _send_pvp_game_result(self, game_id: str, result: str, reason: str, game_info: dict):
        """
        Gửi kết quả game cho PvP game với personalized messages
        
        Args:
            game_id: ID của game
            result: Kết quả game ('white_win', 'black_win', 'draw')
            reason: Lý do kết thúc
            game_info: Thông tin game
        """
        white_fd = game_info.get('white_fd')
        black_fd = game_info.get('black_fd')
        
        # Message cho white player
        if white_fd and white_fd != -1:
            if result == 'draw':
                white_outcome = 'draw'
                white_message = f'Game ended in a draw - {reason}'
            elif result == 'white_win':
                white_outcome = 'you_win'
                white_message = f'You Win! {reason}'
            else:  # black_win
                white_outcome = 'you_loss'
                white_message = f'You Lost! {reason}'
            
            self.network.send_to_client(white_fd, self.MessageTypeS2C.GAME_OVER, {
                'game_id': game_id,
                'result': result,
                'outcome': white_outcome,
                'message': white_message,
                'reason': reason
            })
        
        # Message cho black player
        if black_fd and black_fd != -1:
            if result == 'draw':
                black_outcome = 'draw'
                black_message = f'Game ended in a draw - {reason}'
            elif result == 'black_win':
                black_outcome = 'you_win'
                black_message = f'You Win! {reason}'
            else:  # white_win
                black_outcome = 'you_loss'
                black_message = f'You Lost! {reason}'
            
            self.network.send_to_client(black_fd, self.MessageTypeS2C.GAME_OVER, {
                'game_id': game_id,
                'result': result,
                'outcome': black_outcome,
                'message': black_message,
                'reason': reason
            })
