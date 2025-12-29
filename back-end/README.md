# Chess Game Server - Pure TCP Implementation

Online Chess backend server sử dụng **TCP thuần túy** với C server và Python handlers.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop Clients (PyQt6)                  │
│                 TCP Binary Protocol (Port 8765)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Network Layer (tcp_server/)                    │
│  • server_core.c - C TCP server with poll()                │
│  • protocol.h - Binary protocol (6-byte header)             │
│  • network_bridge.py - Python-C ctypes interface            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Business Logic (handlers/)                     │
│  • auth_handler.py - Register/Login                         │
│  • matchmaking_handler.py - Find match, AI games            │
│  • game_handler.py - Make move, resign, draw                │
│  • stats_handler.py - Stats, history, replay                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Data Layer (services/ + models/)               │
│  • services/user_service.py - User CRUD                     │
│  • services/game_service.py - Game logic & ELO              │
│  • models/user.py - User model                              │
│  • models/game.py - Game model                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    MongoDB Database                         │
│  • users collection - Authentication & ELO                  │
│  • games collection - Game history & PGN                    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Minimal dependencies** (không có WebSocket/HTTP frameworks):
- `pymongo` - MongoDB driver
- `python-dotenv` - Environment variables
- `bcrypt` - Password hashing
- `PyJWT` - Token authentication
- `python-chess` - Chess engine

### 2. Configure MongoDB

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env`:
```env
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=chess_game
JWT_SECRET=your-secret-key-here
```

### 3. Compile C Server

```bash
cd tcp_server
make
cd ..
```

This creates `tcp_server/libchess_server.so` (shared library).

### 4. Run Server

```bash
python3 run_server.py
```

Server starts on `localhost:8765`.

## 📡 TCP Protocol

### Message Format
```
┌──────────────┬──────────────────┬─────────────────────┐
│ Message ID   │ Payload Length   │ Payload (JSON)      │
│ (2 bytes)    │ (4 bytes)        │ (variable length)   │
│ uint16_t BE  │ uint32_t BE      │ UTF-8 encoded       │
└──────────────┴──────────────────┴─────────────────────┘
```

### Message Types

**Client → Server (C2S)**
```python
REGISTER = 0x0001          # {"email", "password", "username"}
LOGIN = 0x0002             # {"email", "password"}
FIND_MATCH = 0x0010        # {} - Find PvP opponent
FIND_AI_MATCH = 0x0012     # {"difficulty", "color"}
MAKE_MOVE = 0x0020         # {"game_id", "move"} - UCI format
RESIGN = 0x0021            # {"game_id"}
OFFER_DRAW = 0x0022        # {"game_id"}
ACCEPT_DRAW = 0x0023       # {"game_id"}
DECLINE_DRAW = 0x0024      # {"game_id"}
GET_STATS = 0x0030         # {}
GET_HISTORY = 0x0031       # {}
```

**Server → Client (S2C)**
```python
REGISTER_RESULT = 0x1001   # {"success", "message", "user_id"}
LOGIN_RESULT = 0x1002      # {"success", "token", "user_id", "rating"}
MATCH_FOUND = 0x1100       # {"opponent_id", "opponent_username", "rating"}
GAME_START = 0x1101        # {"game_id", "color", "fen", "opponent_username"}
GAME_STATE_UPDATE = 0x1200 # {"game_id", "fen", "last_move", "turn"}
INVALID_MOVE = 0x1201      # {"reason"}
GAME_OVER = 0x1202         # {"game_id", "result", "reason"}
```

## 📁 Project Structure

```
back-end/
├── tcp_server/              # Network layer (pure TCP)
│   ├── server_core.c        # C TCP server (poll I/O)
│   ├── protocol.h           # Protocol definitions
│   ├── network_bridge.py    # Python-C bridge (ctypes)
│   ├── Makefile             # Build C server
│   └── test_client.py       # Test TCP client
│
├── handlers/                # Business logic handlers
│   ├── auth_handler.py      # Registration & authentication
│   ├── matchmaking_handler.py # PvP & AI matchmaking
│   ├── game_handler.py      # Game moves & control
│   └── stats_handler.py     # Statistics & history
│
├── services/                # Database operations
│   ├── user_service.py      # User CRUD & auth
│   └── game_service.py      # Game logic & ELO
│
├── models/                  # Data models
│   ├── user.py              # User model
│   └── game.py              # Game model
│
├── utils/                   # Utilities
│   └── jwt_utils.py         # JWT token handling
│
├── chess_server.py          # Main orchestration class
├── run_server.py            # Entry point
├── database.py              # MongoDB connection
└── requirements.txt         # Python dependencies
```

## 🎮 Features

### Authentication
- ✅ User registration with email/password
- ✅ Login with JWT token
- ✅ Password hashing with bcrypt
- ✅ Session management

### Matchmaking
- ✅ PvP matchmaking (automatic pairing)
- ✅ AI opponent (easy/medium/hard)
- ✅ Game state tracking
- ✅ Active games management

### Gameplay
- ✅ Move validation (python-chess)
- ✅ **Real-time move broadcasting** to both players
- ✅ Check/checkmate detection
- ✅ Resign functionality
- ✅ Draw offers & acceptance
- ✅ Game history (PGN format)

### Statistics
- ✅ ELO rating system (K-factor=32)
- ✅ Win/loss/draw tracking
- ✅ Game history with replay
- ✅ Player statistics

## 🔧 Development

### Testing TCP Connection

```bash
cd tcp_server
python3 test_client.py
```

### Debugging

Enable debug logs in `run_server.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Schema

**Users Collection**
```json
{
  "_id": ObjectId,
  "email": "user@example.com",
  "password": "$2b$12$...",  // bcrypt hash
  "username": "player1",
  "elo_rating": 1200,
  "games_played": 0,
  "wins": 0,
  "losses": 0,
  "draws": 0,
  "created_at": ISODate
}
```

**Games Collection**
```json
{
  "_id": ObjectId,
  "game_id": "pvp_1234567890",
  "white_player_id": ObjectId,
  "black_player_id": ObjectId,
  "white_username": "player1",
  "black_username": "player2",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "moves": ["e2e4", "e7e5", ...],
  "pgn": "1. e4 e5 2. Nf3 ...",
  "result": "white_win|black_win|draw",
  "status": "active|completed|resigned",
  "start_time": ISODate,
  "end_time": ISODate
}
```

## 🐛 Common Issues

### C server compilation fails
```bash
# Install GCC if missing
sudo apt-get install build-essential  # Ubuntu/Debian
brew install gcc                       # macOS
```

### MongoDB connection error
```bash
# Start MongoDB service
sudo systemctl start mongod  # Linux
brew services start mongodb-community  # macOS
```

### Port already in use
```bash
# Find process using port 8765
lsof -i :8765
# Kill process
kill -9 <PID>
```

## 📚 Documentation

- [TCP Server Architecture](tcp_server/OOP_ARCHITECTURE.md)
- [Protocol Specification](tcp_server/protocol.h)
- [Test Client](tcp_server/test_client.py)

## 🔍 Why Pure TCP? (No WebSocket/HTTP)

### ✅ Advantages
- **Lower latency**: No HTTP overhead, direct binary protocol
- **Less resource usage**: No web framework (aiohttp/flask/django)
- **Better control**: Custom protocol optimized for chess moves
- **Simpler deployment**: No CORS, SSL, reverse proxy complexity
- **Learning**: Understanding network programming at TCP level

### 🎯 Performance
- Header: Only 6 bytes (vs ~500+ bytes for HTTP)
- Connection: Persistent TCP (vs HTTP request/response cycle)
- Encoding: Binary + JSON (vs full HTTP headers + JSON)

## 👤 Demo Accounts

| Email | Password |
|-------|----------|
| user1@exam.com | 12345678 |
| user2@exam.com | 12345678 |

## 📝 License

Educational project for IT4062 course.
