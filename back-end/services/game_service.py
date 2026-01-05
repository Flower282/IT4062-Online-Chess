"""
Game Service
Xử lý business logic liên quan đến Game
"""
from datetime import datetime
from database import get_db_connection
from models.game import Game
from bson import ObjectId
import chess


def create_game(game_id, white_player_id, black_player_id, 
                white_username, black_username, time_control=None,
                is_ai_game=False, ai_difficulty=None):
    """
    Tạo game mới
    
    Args:
        game_id (str): ID của game
        white_player_id: ID người chơi trắng
        black_player_id: ID người chơi đen (-1 nếu AI)
        white_username (str): Username người chơi trắng
        black_username (str): Username người chơi đen
        time_control (dict): Thời gian kiểm soát
        is_ai_game (bool): Game với AI hay không
        ai_difficulty (str): Độ khó AI
        
    Returns:
        dict: {'success': bool, 'message': str, 'game': dict}
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        
        game = Game(
            game_id=game_id,
            white_player_id=white_player_id,
            black_player_id=black_player_id,
            white_username=white_username,
            black_username=black_username,
            start_time=datetime.utcnow(),
            time_control=time_control,
            is_ai_game=is_ai_game,
            ai_difficulty=ai_difficulty
        )
        
        result = games_collection.insert_one(game.to_dict())
        
        return {
            'success': True,
            'message': 'Game created successfully',
            'game': game.to_dict()
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}


def get_game(game_id):
    """
    Lấy thông tin game theo game_id
    
    Args:
        game_id (str): ID của game
        
    Returns:
        dict: Thông tin game hoặc None
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        
        game_doc = games_collection.find_one({'game_id': game_id})
        
        if game_doc:
            return game_doc
        
        return None
    
    except Exception as e:
        return None


def update_game_state(game_id, move, fen):
    """
    Cập nhật trạng thái game sau một nước đi
    
    Args:
        game_id (str): ID của game
        move (str): Nước đi (UCI format)
        fen (str): FEN string mới
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        
        result = games_collection.update_one(
            {'game_id': game_id},
            {
                '$push': {'moves': move},
                '$set': {'fen': fen}
            }
        )
        
        if result.modified_count > 0:
            return {'success': True, 'message': 'Game state updated'}
        else:
            return {'success': False, 'message': 'Game not found'}
    
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}


def end_game(game_id, result, status='completed'):
    """
    Kết thúc game và cập nhật kết quả
    
    Args:
        game_id (str): ID của game
        result (str): Kết quả (white_win, black_win, draw)
        status (str): Trạng thái (completed, resigned, draw)
        
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        
        update_result = games_collection.update_one(
            {'game_id': game_id},
            {
                '$set': {
                    'status': status,
                    'result': result,
                    'end_time': datetime.utcnow()
                }
            }
        )
        
        if update_result.modified_count > 0:
            # Cập nhật ELO của người chơi
            # Không cập nhật ELO nếu là draw by agreement (status='draw')
            game = get_game(game_id)
            if game and not game['is_ai_game']:
                # Chỉ cập nhật ELO nếu không phải draw by agreement
                if status != 'draw':
                    update_player_elo(game, result)
            
            return {'success': True, 'message': 'Game ended successfully'}
        else:
            return {'success': False, 'message': 'Game not found'}
    
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}


def update_player_elo(game, result):
    """
    Cập nhật ELO của người chơi sau khi game kết thúc
    
    Args:
        game (dict): Thông tin game
        result (str): Kết quả game
    """
    try:
        db = get_db_connection()
        users_collection = db['users']
        
        white_id = game['white_player_id']
        black_id = game['black_player_id']
        
        # Lấy ELO hiện tại
        white_user = users_collection.find_one({'_id': ObjectId(white_id)})
        black_user = users_collection.find_one({'_id': ObjectId(black_id)})
        
        if not white_user or not black_user:
            return
        
        white_elo = white_user.get('elo', 1200)
        black_elo = black_user.get('elo', 1200)
        
        # Tính ELO mới (công thức ELO cơ bản)
        K = 32  # K-factor
        
        expected_white = 1 / (1 + 10 ** ((black_elo - white_elo) / 400))
        expected_black = 1 / (1 + 10 ** ((white_elo - black_elo) / 400))
        
        if result == 'white_win':
            score_white, score_black = 1, 0
        elif result == 'black_win':
            score_white, score_black = 0, 1
        else:  # draw
            score_white, score_black = 0.5, 0.5
        
        new_white_elo = white_elo + K * (score_white - expected_white)
        new_black_elo = black_elo + K * (score_black - expected_black)
        
        # Cập nhật ELO trong database
        users_collection.update_one(
            {'_id': ObjectId(white_id)},
            {'$set': {'elo': round(new_white_elo)}}
        )
        users_collection.update_one(
            {'_id': ObjectId(black_id)},
            {'$set': {'elo': round(new_black_elo)}}
        )
    
    except Exception as e:
        pass


def get_user_game_history(user_id, limit=10):
    """
    Lấy lịch sử game của user
    
    Args:
        user_id: ID của user
        limit (int): Số lượng game tối đa
        
    Returns:
        list: Danh sách games
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        
        games = games_collection.find(
            {
                '$or': [
                    {'white_player_id': user_id},
                    {'black_player_id': user_id}
                ],
                'status': {'$ne': 'active'}
            }
        ).sort('end_time', -1).limit(limit)
        
        result = []
        for game_doc in games:
            # Determine if user won, lost or drew
            game_result = game_doc['result']
            user_is_white = game_doc['white_player_id'] == user_id
            
            # Convert result to user perspective
            if game_result == 'white_win':
                user_result = 'win' if user_is_white else 'loss'
            elif game_result == 'black_win':
                user_result = 'win' if not user_is_white else 'loss'
            elif game_result == 'draw':
                user_result = 'draw'
            else:
                user_result = 'in_progress'
            
            # Convert created_at datetime to string
            created_at = game_doc.get('created_at', game_doc.get('end_time'))
            created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'N/A'
            
            result.append({
                'game_id': game_doc['game_id'],
                'opponent': game_doc['black_username'] if user_is_white else game_doc['white_username'],
                'result': game_result,  # Original result
                'user_result': user_result,  # User's perspective
                'my_color': 'white' if user_is_white else 'black',
                'date': game_doc['end_time'].strftime('%Y-%m-%d %H:%M') if game_doc.get('end_time') else 'N/A',
                'created_at': created_at_str,
                'moves_count': len(game_doc['moves']),
                'is_ai_game': game_doc.get('is_ai_game', False),
                'white_username': game_doc['white_username'],
                'black_username': game_doc['black_username']
            })
        
        return result
    
    except Exception as e:
        return []


def get_user_stats(user_id):
    """
    Lấy thống kê của user
    
    Args:
        user_id: ID của user
        
    Returns:
        dict: Thống kê
    """
    try:
        db = get_db_connection()
        games_collection = db[Game.get_collection_name()]
        users_collection = db['users']
        
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return None
        
        # Đếm số trận thắng, thua, hòa
        wins = games_collection.count_documents({
            '$or': [
                {'white_player_id': user_id, 'result': 'white_win'},
                {'black_player_id': user_id, 'result': 'black_win'}
            ]
        })
        
        losses = games_collection.count_documents({
            '$or': [
                {'white_player_id': user_id, 'result': 'black_win'},
                {'black_player_id': user_id, 'result': 'white_win'}
            ]
        })
        
        draws = games_collection.count_documents({
            '$or': [
                {'white_player_id': user_id, 'result': 'draw'},
                {'black_player_id': user_id, 'result': 'draw'}
            ]
        })
        
        total_games = wins + losses + draws
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        
        return {
            'user_id': str(user['_id']),
            'username': user['username'],
            'fullname': user['fullname'],
            'elo': user.get('elo', 1200),
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'total_games': total_games,
            'win_rate': round(win_rate, 2)
        }
    
    except Exception as e:
        return None


def validate_move(game_id, move):
    """
    Kiểm tra tính hợp lệ của nước đi
    
    Args:
        game_id (str): ID của game
        move (str): Nước đi (UCI format, ví dụ: e2e4, e7e8q cho promotion)
        
    Returns:
        dict: {'valid': bool, 'fen': str, 'game_over': bool, 'result': str}
    """
    try:
        game = get_game(game_id)
        if not game:
            return {'valid': False, 'reason': 'Game not found'}
        
        board = chess.Board(game['fen'])
        
        try:
            # Parse UCI move (handles promotion automatically if present)
            chess_move = chess.Move.from_uci(move)
            print(f"🔍 Validating move: {move} (from_uci: {chess_move})")
            
            if chess_move in board.legal_moves:
                board.push(chess_move)
                
                # Kiểm tra game over
                game_over = board.is_game_over()
                result = 'ongoing'
                
                if game_over:
                    if board.is_checkmate():
                        # board.turn là lượt của người bị checkmate (không thể đi)
                        # Nếu board.turn == WHITE → trắng bị checkmate → đen thắng
                        # Nếu board.turn == BLACK → đen bị checkmate → trắng thắng
                        result = 'black_win' if board.turn == chess.WHITE else 'white_win'
                    elif board.is_stalemate() or board.is_insufficient_material():
                        result = 'draw'
                
                return {
                    'valid': True,
                    'fen': board.fen(),
                    'game_over': game_over,
                    'result': result,
                    'in_check': board.is_check()
                }
            else:
                return {'valid': False, 'reason': 'Illegal move'}
        
        except ValueError as e:
            return {'valid': False, 'reason': f'Invalid move format: {str(e)}'}
    
    except Exception as e:
        return {'valid': False, 'reason': str(e)}


def get_game_pgn(game_id):
    """
    Tạo PGN string cho game
    
    Args:
        game_id (str): ID của game
        
    Returns:
        str: PGN string hoặc None
    """
    try:
        game = get_game(game_id)
        if not game:
            return None
        
        # Tạo PGN header
        pgn = f'[Event "Online Chess Game"]\n'
        pgn += f'[Site "IT4062 Chess Platform"]\n'
        pgn += f'[Date "{game["start_time"].strftime("%Y.%m.%d") if game.get("start_time") else "????.??.??"}"\n'
        pgn += f'[White "{game["white_username"]}"]\n'
        pgn += f'[Black "{game["black_username"]}"]\n'
        pgn += f'[Result "{"1-0" if game["result"] == "white_win" else "0-1" if game["result"] == "black_win" else "1/2-1/2" if game["result"] == "draw" else "*"}"]\n'
        pgn += f'[WhiteElo "?"]\n'
        pgn += f'[BlackElo "?"]\n\n'
        
        # Thêm moves
        board = chess.Board()
        move_number = 1
        moves_text = ""
        
        for i, uci_move in enumerate(game['moves']):
            try:
                move = chess.Move.from_uci(uci_move)
                san_move = board.san(move)
                board.push(move)
                
                if i % 2 == 0:
                    moves_text += f"{move_number}. {san_move} "
                else:
                    moves_text += f"{san_move} "
                    move_number += 1
            except:
                pass
        
        pgn += moves_text
        
        return pgn
    
    except Exception as e:
        print(f"Error generating PGN: {e}")
        return None
