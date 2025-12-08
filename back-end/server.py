from aiohttp import web
import aiohttp_cors
import socketio
import random
import os
import io
import json
import chess
import chess.pgn
from engine import Engine
import time
from multiprocessing.pool import ThreadPool
from threading import Thread
from database import get_db_connection
from pymongo.errors import ConnectionFailure
from routes import setup_routes

sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Setup routes trước khi setup CORS
setup_routes(app)

# Setup CORS
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*",
        allow_methods="*"
    )
})

# Thêm CORS cho tất cả routes (trừ socket.io)
for route in list(app.router.routes()):
    # Bỏ qua socket.io routes vì chúng đã có CORS riêng
    if not route.resource.canonical.startswith('/socket.io'):
        try:
            cors.add(route)
        except ValueError:
            # Route đã có CORS, bỏ qua
            pass

games = []
rooms = []
tot_client = 0
# Mapping userId -> socket.id for targeting specific users
user_sockets = {}  # {username: sid}
# Live online users tracking
online_users = {}  # {sid: {username, fullname, elo}}

engine = Engine()

pool = ThreadPool(processes=10)

def check_db_connection():
    """Kiểm tra kết nối đến MongoDB"""
    try:
        db = get_db_connection()
        # Thử ping database để kiểm tra kết nối
        db.client.admin.command('ping')
        print("✓ Database connection successful")
        return True
    except ConnectionFailure as e:
        print(f"✗ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error checking database connection: {e}")
        return False

@sio.event
def connect(sid, environ):
    global tot_client

    for room in rooms:
        if len(room['sids']) == 0 and time.time() - room['last_seen'] > 30.0:
            for game in games:
                if game['id'] == room['id']:
                    games.remove(game)
            rooms.remove(room)

    tot_client += 1
    print(f"Socket connected: {sid}, Total clients: {tot_client}")
    #log()

@sio.event
async def user_login(sid, data):
    """Handle user login - add to online users and broadcast"""
    username = data.get('username')
    fullname = data.get('fullname', username)
    elo = data.get('elo', 1200)
    
    if username:
        # Add to online users
        online_users[sid] = {
            'username': username,
            'fullname': fullname,
            'elo': elo
        }
        
        # Also add to user_sockets for challenge feature
        user_sockets[username] = sid
        
        print(f"User logged in: {username} (sid: {sid})")
        print(f"Online users count: {len(online_users)}")
        
        # Broadcast updated online users list to ALL clients
        users_list = list(online_users.values())
        await sio.emit('update_online_users', {'users': users_list})

@sio.event
async def register_user(sid, data):
    """Register user with their socket id for challenge feature"""
    username = data.get('username')
    if username:
        user_sockets[username] = sid
        print(f"User {username} registered with socket {sid}")
        await sio.emit('user_registered', {'username': username}, room=sid)

@sio.event
async def send_challenge(sid, data):
    """Handle challenge request from sender to receiver"""
    target_username = data.get('targetUsername')
    sender_info = data.get('senderInfo')  # {username, fullname, elo}
    
    if target_username in user_sockets:
        target_sid = user_sockets[target_username]
        # Send challenge notification to target user
        await sio.emit('receive_challenge', {
            'senderInfo': sender_info
        }, room=target_sid)
        
        # Confirm to sender that challenge was sent
        await sio.emit('challenge_sent', {
            'targetUsername': target_username
        }, room=sid)
    else:
        # Target user not online
        await sio.emit('challenge_failed', {
            'message': 'Người chơi không online'
        }, room=sid)

@sio.event
async def respond_challenge(sid, data):
    """Handle challenge response (accept/decline)"""
    status = data.get('status')  # 'accepted' or 'declined'
    sender_username = data.get('senderUsername')
    responder_info = data.get('responderInfo')  # {username, fullname}
    
    if sender_username in user_sockets:
        sender_sid = user_sockets[sender_username]
        
        if status == 'accepted':
            # Create a new game for both players
            game_id = ''.join(random.choice(
                '0123456789abcdefghijklmnopqrstuvwxyz') for i in range(4))
            
            games.append({
                'id': game_id,
                'players': [sender_username, responder_info['username']],
                'pgn': '',
                'type': 'multiplayer',
                'status': 'starting'
            })
            
            # Add both users to the game room
            await sio.enter_room(sender_sid, game_id)
            await sio.enter_room(sid, game_id)
            rooms.append({
                'id': game_id, 
                'sids': [sender_sid, sid], 
                'last_seen': time.time()
            })
            
            # Notify both players to start game
            await sio.emit('game_start', {
                'gameId': game_id,
                'opponent': responder_info
            }, room=sender_sid)
            
            await sio.emit('game_start', {
                'gameId': game_id,
                'opponent': {'username': sender_username}
            }, room=sid)
            
        else:  # declined
            # Notify sender that challenge was declined
            await sio.emit('challenge_declined', {
                'responder': responder_info
            }, room=sender_sid)

@sio.event
async def create(sid, data):
    game_id = ''.join(random.choice(
        '0123456789abcdefghijklmnopqrstuvwxyz') for i in range(4))
    games.append({
        'id': game_id,
        'players': [data['username']],
        'pgn': '',
        'type': 'multiplayer',
        'status': 'starting'
    })

    await sio.enter_room(sid, game_id)
    rooms.append({'id': game_id, 'sids': [sid], 'last_seen': time.time()})
    await sio.emit('created', {'game': games[len(games)-1]})

    #log()

@sio.event
async def fetch(sid, data):
    for game in games:
        if game['id'] == data['id']:
            for room in rooms:
                if room['id'] == data['id']:
                    # (NOTE) aggiunto mo'
                    if sid not in room['sids']:
                        room['sids'].append(sid)
                        await sio.enter_room(sid, data['id'])

                    print(room['sids'])

                    if len(room['sids']) < 2 and room['sids'][0] != sid:
                        room['sids'].append(sid)
                        await sio.enter_room(sid, data['id'])
            
            if game['status'] == 'starting' and game['type'] == 'computer' and game['players'][0] == game['ai']:
                board = chess.Board()
                if game['ai'] == 'random':
                    move = engine.get_random_move(board)
                elif game['ai'] == 'stockfish':
                    move = engine.get_stockfish_best_move(board)
                elif game['ai'] == 'minimax':
                    move = str(engine.get_minimax_best_move(board, False))
                elif game['ai'] == 'ml':
                    move = str(engine.get_minimax_best_move(board, True))

                move_from = move[:2]
                move_to = str(move)[2:]

                await sio.emit('moved', {'from': move_from, 'to': move_to}, room = data['id'])
                board = chess.Board()
                game['pgn'] = str(board.variation_san([chess.Move.from_uci(m) for m in [move]]))

            game['status'] = 'ongoing'
            await sio.emit('fetch', {'game': game}, room=data['id'])

    #log()

@sio.event
async def join(sid, data):
    gamefound = False
    username_already_in_use = False
    for game in games:
        if game['id'] == data['id']:
            if game['players'][0] == data['username']:
                username_already_in_use = True
            else:
                game['players'].append(data['username'])
                game['status'] = 'ongoing'
                sio.enter_room(sid, data['id'])
                for room in rooms:
                    if room['id'] == data['id']:
                        room['sids'].append(sid)

                await sio.emit('joined', {'game': game})
                gamefound = True

    if not gamefound:
        await sio.emit('gamenotfound')

    if username_already_in_use:
        await sio.emit('usernamealreadyinuse')

    #log()

@sio.event
async def move(sid, data):  # id, from, to, pgn

    for game in games:
        if game['id'] == data['id']:
            game['pgn'] = data['pgn']
            if game['type'] == 'computer':
                pgn = io.StringIO(data['pgn'])
                chess_game = chess.pgn.read_game(pgn)
                board = chess_game.board()
                for move in chess_game.mainline_moves():
                    board.push(move)

                if board.is_checkmate():
                    await sio.emit('checkmate', room=data['id'])
                    await sio.emit('fetch', {'game': game}, room = data['id'])
                    index = -1
                    for g in games:
                        if g['id'] == g['id']:
                            index = games.index(g)

                    if index > -1:
                        games.pop(index)

                    #log()
                    return
                
                if board.is_stalemate() or board.is_fivefold_repetition() or board.is_insufficient_material():
                    await sio.emit('draw', room=data['id'])
                    index = -1
                    for g in games:
                        if g['id'] == data['id']:
                            index = games.index(g)

                    if index > -1:
                        games.pop(index)
                    
                    #log()
                    return
                
                move = ''

                if game['ai'] == 'random':
                    move = engine.get_random_move(board)
                elif game['ai'] == 'stockfish':
                    move = engine.get_stockfish_best_move(board)
                elif game['ai'] == 'minimax':
                    move = str(engine.get_minimax_best_move(board, False))
                elif game['ai'] == 'ml':
                    async_result = pool.apply_async(engine.get_minimax_best_move, (board, True))
                    move = str(async_result.get())

                move_from = move[:2]
                move_to = str(move)[2:]
                if(len(move_to) > 2): # promotion
                    move_to = move_to.rstrip(move_to[-1])


                await sio.emit('moved', {'from': move_from, 'to': move_to}, room = data['id'])

                chess_game.end().add_main_variation(chess.Move.from_uci(move))
                game['pgn'] = str(chess_game.variations[0])

                await sio.emit('fetch', {'game': game}, room = data['id'])


            elif game['type'] == 'multiplayer':
                await sio.emit('moved', {'from': data['from'],'to': data['to'] }, room = data['id'], skip_sid=sid)
                await sio.emit('fetch', {'game': game}, room = data['id'])

    #log()

@sio.event
async def resign(sid, data):
    await sio.emit('resigned', room=data['id'], skip_sid=sid)
    index = -1
    for game in games:
        if game['id'] == data['id']:
            index = games.index(game)

    if index > -1:
        games.pop(index)
    
    #log()

@sio.event
async def checkmate(sid, data):
    await sio.emit('checkmate', room=data['id'], skip_sid=sid)
    index = -1
    for game in games:
        if game['id'] == data['id']:
            index = games.index(game)

    if index > -1:
        games.pop(index)
    
    #log()

@sio.event
async def draw(sid, data):
    await sio.emit('draw', room=data['id'], skip_sid=sid)
    index = -1
    for game in games:
        if game['id'] == data['id']:
            index = games.index(game)

    if index > -1:
        games.pop(index)
    
    #log()

@sio.event
async def disconnect(sid):
    global tot_client

    print('disconnect', sid)
    tot_client -= 1
    
    # Remove user from online_users
    if sid in online_users:
        disconnected_user = online_users[sid]
        username = disconnected_user['username']
        
        # Remove from online_users
        del online_users[sid]
        
        # Remove from user_sockets mapping
        if username in user_sockets and user_sockets[username] == sid:
            del user_sockets[username]
        
        print(f"User {username} disconnected (sid: {sid})")
        print(f"Online users count: {len(online_users)}")
        
        # Broadcast updated online users list to ALL remaining clients
        users_list = list(online_users.values())
        await sio.emit('update_online_users', {'users': users_list})
    
    for room in rooms:
        if sid in room['sids']:
            await sio.emit('disconnected', room=room['id'])
            room['sids'].remove(sid)
            room['last_seen'] = time.time()

        # if len(room['sids']) == 0:
        #     for game in games:
        #         if game['id'] == room['id']:
        #             if game['type'] != 'computer':
        #                 games.remove(game)
            
        #     if game['type'] != 'computer':
        #         rooms.remove(room)

    #log()


@sio.event
async def createComputerGame(sid, data):
    game_id = ''.join(random.choice(
        '0123456789abcdefghijklmnopqrstuvwxyz') for i in range(4))

    players = [data['username'], data['ai']]
    #random.shuffle(players)
    games.append({
        'id': game_id,
        'players': players,
        'pgn': '',
        'type': 'computer',
        'ai': data['ai'],
        'status': 'starting'
    })

    await sio.enter_room(sid, game_id)
    rooms.append({'id': game_id, 'sids': [sid], 'last_seen': time.time()})
    await sio.emit('createdComputerGame', {'game': games[len(games)-1]})

    #log()


def log():
    os.system('clear')

    print(f'Users connected: {tot_client}')

    print(f'GAMES: ')

    print(json.dumps(games, indent=2))

    print(f'ROOMS: ')

    print(json.dumps(rooms, indent=2))

if __name__ == '__main__':
    #log()
    
    # Kiểm tra kết nối database trước khi khởi động server
    print("Checking database connection...")
    if not check_db_connection():
        print("Warning: Server starting without database connection")
    
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, port=port)
