# Kiến Trúc Hệ Thống - Online Chess

## 1. Kiến Trúc Tổng Quan (High-Level Architecture)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DESKTOP CLIENT (PyQt6)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Login Window │  │ Lobby Window │  │ Game Window  │  │Chess Board  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                  │                  │                  │        │
│         └──────────────────┴──────────────────┴──────────────────┘        │
│                                    │                                      │
│                         ┌──────────▼──────────┐                          │
│                         │  NetworkClient (Qt) │                          │
│                         └──────────┬──────────┘                          │
└────────────────────────────────────┼───────────────────────────────────┘
                                     │
                          ┌──────────▼───────────┐
                          │ NetworkBridge Client │ (Python ctypes wrapper)
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │  TCP Client Core (C) │ (Compiled .so library)
                          └──────────┬───────────┘
                                     │
                    ═════════════════╪═══════════════════
                         TCP/IP Socket Connection
                    ═════════════════╪═══════════════════
                                     │
                          ┌──────────▼───────────┐
                          │  TCP Server Core (C) │ (Compiled .so library)
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │ NetworkManager       │ (Python ctypes wrapper)
                          └──────────┬───────────┘
                                     │
┌────────────────────────────────────┼───────────────────────────────────┐
│                       BACKEND SERVER (Python)                            │
│                         ┌──────────▼──────────┐                         │
│                         │  ChessGameServer    │                         │
│                         └──────────┬──────────┘                         │
│                                    │                                     │
│         ┌──────────────────────────┼──────────────────────────┐         │
│         │                          │                           │         │
│  ┌──────▼──────┐         ┌─────────▼────────┐      ┌─────────▼──────┐  │
│  │ AuthHandler │         │ GameHandler      │      │ MatchHandler   │  │
│  └──────┬──────┘         └─────────┬────────┘      └─────────┬──────┘  │
│         │                          │                          │         │
│  ┌──────▼──────┐         ┌─────────▼────────┐      ┌─────────▼──────┐  │
│  │StatsHandler │         │   WinHandler     │      │ Other Handlers │  │
│  └──────┬──────┘         └─────────┬────────┘      └─────────┬──────┘  │
│         │                          │                          │         │
│         └──────────────────────────┼──────────────────────────┘         │
│                                    │                                     │
│                         ┌──────────▼──────────┐                         │
│                         │     Services        │                         │
│                         │  - UserService      │                         │
│                         │  - GameService      │                         │
│                         └──────────┬──────────┘                         │
│                                    │                                     │
│                         ┌──────────▼──────────┐                         │
│                         │  Database Layer     │                         │
│                         │   (MongoDB)         │                         │
│                         └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Luồng Giao Tiếp Client-Server (Communication Flow)

```
CLIENT                                                    SERVER
  │                                                         │
  │ 1. Connect to Server                                   │
  │────────────────────────────────────────────────────────>│
  │                                                         │ NetworkManager
  │<────────────────────────────────────────────────────────│ accepts connection
  │                      CONNECTED                          │
  │                                                         │
  │ 2. Send LOGIN (0x0002)                                 │
  │ { username, password }                                 │
  │────────────────────────────────────────────────────────>│
  │                                                         │ AuthHandler
  │                                                         │ verify_user()
  │                                                         │ 
  │<────────────────────────────────────────────────────────│ LOGIN_RESULT (0x1002)
  │          { success, user_id, elo, ... }                │
  │                                                         │
  │ 3. Send FIND_MATCH (0x0010)                            │
  │────────────────────────────────────────────────────────>│
  │                                                         │ MatchmakingHandler
  │                                                         │ add to queue
  │                                                         │ find opponent
  │<────────────────────────────────────────────────────────│ MATCH_FOUND (0x1100)
  │         { opponent_info, ... }                          │
  │<────────────────────────────────────────────────────────│ GAME_START (0x1101)
  │         { game_id, color, fen, ... }                    │
  │                                                         │
  │ 4. Send MAKE_MOVE (0x0020)                             │
  │ { game_id, move: "e2e4" }                              │
  │────────────────────────────────────────────────────────>│
  │                                                         │ GameHandler
  │                                                         │ validate_move()
  │                                                         │ update_game_state()
  │<────────────────────────────────────────────────────────│ GAME_STATE_UPDATE (0x1200)
  │         { fen, last_move, turn, ... }                   │
  │                                                         │
  │ ... game continues ...                                  │
  │                                                         │
  │ 5. Send RESIGN (0x0021)                                │
  │────────────────────────────────────────────────────────>│
  │                                                         │ GameHandler
  │                                                         │ end_game()
  │                                                         │ WinHandler
  │<────────────────────────────────────────────────────────│ GAME_OVER (0x1202)
  │         { outcome: "you_loss", ... }                    │
  │                                                         │
```

## 3. Kiến Trúc Chi Tiết Desktop Client

```
┌─────────────────────────────────────────────────────────────┐
│                    ChessApplication (QStackedWidget)         │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │   Login    │  │   Lobby    │  │    Game    │           │
│  │   Window   │  │   Window   │  │   Window   │           │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘           │
│        │                │                │                   │
│        └────────────────┴────────────────┘                   │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │   NetworkClient     │                        │
│              │   (Qt Signals)      │                        │
│              │                     │                        │
│              │  Signals:           │                        │
│              │  - connected        │                        │
│              │  - disconnected     │                        │
│              │  - message_received │                        │
│              │  - error_occurred   │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │  NetworkBridge      │                        │
│              │  (ctypes wrapper)   │                        │
│              │                     │                        │
│              │  - send_message()   │                        │
│              │  - poll()           │                        │
│              │  - process_events() │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│              ┌──────────▼──────────┐                        │
│              │  client_core.so     │                        │
│              │  (C Library)        │                        │
│              │                     │                        │
│              │  - client_init()    │                        │
│              │  - client_poll()    │                        │
│              │  - client_send()    │                        │
│              └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 4. Kiến Trúc Chi Tiết Backend Server

```
┌─────────────────────────────────────────────────────────────┐
│                    ChessGameServer                           │
│                                                              │
│              ┌──────────────────────┐                       │
│              │  NetworkManager      │                       │
│              │  (Python wrapper)    │                       │
│              │                      │                       │
│              │  - register_handler()│                       │
│              │  - send_to_client()  │                       │
│              │  - broadcast()       │                       │
│              └──────────┬───────────┘                       │
│                         │                                    │
│              ┌──────────▼───────────┐                       │
│              │   server_core.so     │                       │
│              │   (C Library)        │                       │
│              │                      │                       │
│              │   - server_init()    │                       │
│              │   - server_poll()    │                       │
│              │   - send_message()   │                       │
│              └──────────────────────┘                       │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐                │
│  │  Message        │  │  Client          │                 │
│  │  Handlers       │  │  Sessions        │                 │
│  │                 │  │  {fd: session}   │                 │
│  │ - Auth          │  │                  │                 │
│  │ - Game          │  │  - user_id       │                 │
│  │ - Matchmaking   │  │  - username      │                 │
│  │ - Stats         │  │  - state         │                 │
│  │ - Win           │  │  - game_id       │                 │
│  └────────┬────────┘  └──────────────────┘                 │
│           │                                                  │
│  ┌────────▼─────────┐                                      │
│  │   Services       │                                       │
│  │                  │                                       │
│  │ ┌──────────────┐ │                                      │
│  │ │ UserService  │ │                                      │
│  │ │ - create     │ │                                      │
│  │ │ - verify     │ │                                      │
│  │ │ - get        │ │                                      │
│  │ └──────────────┘ │                                      │
│  │                  │                                       │
│  │ ┌──────────────┐ │                                      │
│  │ │ GameService  │ │                                      │
│  │ │ - create     │ │                                      │
│  │ │ - validate   │ │                                      │
│  │ │ - update     │ │                                      │
│  │ │ - end_game   │ │                                      │
│  │ └──────────────┘ │                                      │
│  └────────┬─────────┘                                      │
│           │                                                  │
│  ┌────────▼─────────┐                                      │
│  │    Database      │                                       │
│  │    (MongoDB)     │                                       │
│  │                  │                                       │
│  │  Collections:    │                                       │
│  │  - users         │                                       │
│  │  - games         │                                       │
│  └──────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
```

## 5. Protocol Message Flow (Chi Tiết)

```
MESSAGE STRUCTURE:
┌──────────┬────────────────┬──────────────────────┐
│  Header  │  Message ID    │      Payload         │
│ (6 bytes)│  (2 bytes)     │   (JSON, variable)   │
└──────────┴────────────────┴──────────────────────┘

Header Format:
  - message_id:      uint16_t (2 bytes)
  - payload_length:  uint32_t (4 bytes)

Example Messages:

1. LOGIN Request (C2S):
   Message ID: 0x0002
   Payload: {"username": "player1", "password": "secret"}
   
2. LOGIN Response (S2C):
   Message ID: 0x1002
   Payload: {"success": true, "user_id": "123", "elo": 1200, ...}
   
3. MAKE_MOVE Request (C2S):
   Message ID: 0x0020
   Payload: {"game_id": "abc123", "move": "e2e4"}
   
4. GAME_STATE_UPDATE (S2C):
   Message ID: 0x1200
   Payload: {"game_id": "abc123", "fen": "...", "turn": "black", ...}
```

## 6. Message Types Overview

### Client to Server (C2S)
```
Authentication:
  0x0001  REGISTER           - Đăng ký tài khoản mới
  0x0002  LOGIN              - Đăng nhập
  0x0003  GET_ONLINE_USERS   - Lấy danh sách người chơi online

Matchmaking:
  0x0010  FIND_MATCH         - Tìm trận đấu
  0x0011  CANCEL_FIND_MATCH  - Hủy tìm trận
  0x0012  FIND_AI_MATCH      - Tìm trận với AI
  0x0025  CHALLENGE          - Thách đấu người chơi
  0x0026  ACCEPT_CHALLENGE   - Chấp nhận thách đấu
  0x0027  DECLINE_CHALLENGE  - Từ chối thách đấu

Game Control:
  0x0020  MAKE_MOVE          - Thực hiện nước đi
  0x0021  RESIGN             - Đầu hàng
  0x0022  OFFER_DRAW         - Đề nghị hòa
  0x0023  ACCEPT_DRAW        - Chấp nhận hòa
  0x0024  DECLINE_DRAW       - Từ chối hòa

Statistics:
  0x0030  GET_STATS          - Lấy thống kê
  0x0031  GET_HISTORY        - Lấy lịch sử đấu
```

### Server to Client (S2C)
```
Authentication:
  0x1001  REGISTER_RESULT    - Kết quả đăng ký
  0x1002  LOGIN_RESULT       - Kết quả đăng nhập
  0x1003  USER_STATUS_UPDATE - Cập nhật trạng thái user
  0x1004  ONLINE_USERS_LIST  - Danh sách người chơi

Matchmaking:
  0x1100  MATCH_FOUND        - Tìm thấy trận đấu
  0x1101  GAME_START         - Bắt đầu game
  0x1205  CHALLENGE_RECEIVED - Nhận thách đấu
  0x1206  CHALLENGE_ACCEPTED - Thách đấu được chấp nhận
  0x1207  CHALLENGE_DECLINED - Thách đấu bị từ chối

Game State:
  0x1200  GAME_STATE_UPDATE  - Cập nhật trạng thái game
  0x1201  INVALID_MOVE       - Nước đi không hợp lệ
  0x1202  GAME_OVER          - Kết thúc game
  0x1203  DRAW_OFFER_RECEIVED- Nhận đề nghị hòa
  0x1204  DRAW_OFFER_DECLINED- Đề nghị hòa bị từ chối

Statistics:
  0x1300  STATS_RESPONSE     - Phản hồi thống kê
  0x1301  HISTORY_RESPONSE   - Phản hồi lịch sử
```

## 7. Technology Stack

```
CLIENT SIDE:
┌─────────────────────────────────────┐
│ UI Layer:        PyQt6              │
│ Language:        Python 3.x         │
│ Chess Engine:    python-chess       │
│ Network:         C (ctypes wrapper) │
│ Config:          python-dotenv      │
└─────────────────────────────────────┘

SERVER SIDE:
┌─────────────────────────────────────┐
│ Framework:       Custom (OOP)       │
│ Language:        Python 3.x         │
│ Network:         C (ctypes wrapper) │
│ Database:        MongoDB            │
│ Chess Engine:    python-chess       │
│ Auth:            bcrypt + PyJWT     │
└─────────────────────────────────────┘

NETWORK LAYER:
┌─────────────────────────────────────┐
│ Protocol:        TCP/IP             │
│ Format:          Binary + JSON      │
│ Implementation:  C (compiled .so)   │
│ Event Model:     poll() based       │
└─────────────────────────────────────┘
```

## 8. Deployment Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Production Setup                       │
│                                                           │
│  ┌────────────────┐         ┌────────────────┐          │
│  │  Desktop App   │         │  Desktop App   │          │
│  │  (Client 1)    │         │  (Client N)    │          │
│  └───────┬────────┘         └───────┬────────┘          │
│          │                          │                     │
│          │      ┌──────────────────┐│                    │
│          └──────┤  Server Machine  ├┘                    │
│                 │                  │                      │
│                 │ ┌──────────────┐ │                     │
│                 │ │ Chess Server │ │                     │
│                 │ │ (Python)     │ │                     │
│                 │ │ Port: 8765   │ │                     │
│                 │ └──────┬───────┘ │                     │
│                 │        │         │                      │
│                 │ ┌──────▼───────┐ │                     │
│                 │ │   MongoDB    │ │                     │
│                 │ │ Port: 27017  │ │                     │
│                 │ └──────────────┘ │                     │
│                 └──────────────────┘                      │
│                                                           │
│  Configuration:                                           │
│  - Server: 0.0.0.0:8765 (listen all interfaces)         │
│  - Client: <server-ip>:8765 (connect to server)         │
│  - MongoDB: localhost:27017 (local to server)            │
└──────────────────────────────────────────────────────────┘
```

## 9. Key Design Patterns

1. **Bridge Pattern**: Python <-> C network layer
2. **Observer Pattern**: Qt Signals/Slots for events
3. **Strategy Pattern**: Different handlers cho message types
4. **Service Layer**: Business logic tách biệt khỏi network
5. **Repository Pattern**: Database access through services
6. **Event-Driven**: poll() based non-blocking I/O

## 10. Configuration Management

```
Desktop App:
  desktop-app/.env
  ├── SERVER_HOST=localhost
  └── SERVER_PORT=8765

Backend Server:
  back-end/.env
  ├── SERVER_HOST=0.0.0.0
  ├── SERVER_PORT=8765
  ├── MONGODB_URI=mongodb://localhost:27017/
  └── DATABASE_NAME=chess_game
```
