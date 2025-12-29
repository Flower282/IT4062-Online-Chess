"""
Game Model
Định nghĩa schema và các thuộc tính của Game
"""

class Game:
    """
    Model Game với các thuộc tính:
    - _id: ID của game (MongoDB ObjectId)
    - game_id: Game ID dạng string (unique)
    - white_player_id: ID người chơi quân trắng
    - black_player_id: ID người chơi quân đen (-1 nếu là AI)
    - white_username: Username người chơi trắng
    - black_username: Username người chơi đen
    - moves: Danh sách các nước đi (UCI format)
    - fen: FEN string của bàn cờ hiện tại
    - status: Trạng thái game (active, completed, resigned, draw)
    - result: Kết quả (white_win, black_win, draw, ongoing)
    - start_time: Thời gian bắt đầu
    - end_time: Thời gian kết thúc
    - time_control: Thời gian kiểm soát (initial, increment)
    - is_ai_game: Game với AI hay không
    - ai_difficulty: Độ khó AI (easy, medium, hard)
    """
    
    def __init__(self, game_id, white_player_id, black_player_id, 
                 white_username, black_username, moves=None, 
                 fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
                 status='active', result='ongoing', start_time=None, end_time=None,
                 time_control=None, is_ai_game=False, ai_difficulty=None, _id=None):
        self._id = _id
        self.game_id = game_id
        self.white_player_id = white_player_id
        self.black_player_id = black_player_id
        self.white_username = white_username
        self.black_username = black_username
        self.moves = moves if moves else []
        self.fen = fen
        self.status = status
        self.result = result
        self.start_time = start_time
        self.end_time = end_time
        self.time_control = time_control if time_control else {'initial': 600, 'increment': 5}
        self.is_ai_game = is_ai_game
        self.ai_difficulty = ai_difficulty
    
    def to_dict(self):
        """Chuyển đổi object thành dictionary"""
        data = {
            'game_id': self.game_id,
            'white_player_id': self.white_player_id,
            'black_player_id': self.black_player_id,
            'white_username': self.white_username,
            'black_username': self.black_username,
            'moves': self.moves,
            'fen': self.fen,
            'status': self.status,
            'result': self.result,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'time_control': self.time_control,
            'is_ai_game': self.is_ai_game,
            'ai_difficulty': self.ai_difficulty
        }
        
        if self._id:
            data['_id'] = str(self._id)
            
        return data
    
    @staticmethod
    def get_collection_name():
        """Trả về tên collection trong MongoDB"""
        return 'games'
