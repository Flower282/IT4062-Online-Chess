# Chess Game Server - OOP Architecture

## 📁 Cấu trúc thư mục mới (Refactored)

```
back-end/
├── tcp_server/                 # 🔌 Network Layer Only
│   ├── protocol.h              # C protocol definitions
│   ├── server_core.c           # C TCP server với poll()
│   ├── network_bridge.py       # NetworkManager (low-level)
│   ├── test_client.py          # Test client
│   └── Makefile                # Build system
│
├── handlers/                   # 📦 Business Logic Handlers
│   ├── __init__.py
│   ├── auth_handler.py         # Authentication logic
│   ├── game_handler.py         # Game logic (moves, resign, draw)
│   ├── matchmaking_handler.py  # Matchmaking & AI games
│   └── stats_handler.py        # Stats & history
│
├── models/                     # 💾 Data Models
│   ├── user.py                 # User model
│   └── game.py                 # Game model
│
├── services/                   # 🔧 Business Services
│   ├── user_service.py         # User business logic
│   └── game_service.py         # Game business logic
│
├── chess_server.py            # 🎯 Main Server Class
├── run_server.py              # 🚀 Entry Point
└── database.py                # 🗄️ Database connection
```

## 🏗️ Kiến trúc OOP

### Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    run_server.py                        │  Entry Point
│                  (Main Entry Point)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 chess_server.py                         │  Orchestration
│              (ChessGameServer Class)                    │
└─────┬──────────────┬──────────────┬──────────────┬─────┘
      │              │              │              │
┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│   Auth    │ │   Game    │ │Matchmaking│ │   Stats   │  Business Logic
│  Handler  │ │  Handler  │ │  Handler  │ │  Handler  │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │              │              │              │
      └──────────────┴──────┬───────┴──────────────┘
                            │
                     ┌──────▼──────┐
                     │  Services   │  Business Services
                     │ (user/game) │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │   Models    │  Data Models
                     │ (user/game) │
                     └──────┬──────┘
                            │
      ┌─────────────────────┴─────────────────────┐
      │                                           │
┌─────▼──────┐                            ┌──────▼──────┐
│  Database  │                            │tcp_server/  │  Network Layer
│  MongoDB   │                            │  (C + Py)   │
└────────────┘                            └─────────────┘
```

### 1. **ChessGameServer** (chess_server.py)
Main server class kết nối tất cả components:
```python
class ChessGameServer:
    - __init__(port)              # Initialize với port
    - _register_handlers()        # Register tất cả handlers
    - start()                     # Start server
    - stop()                      # Stop server
    - run_forever()               # Run event loop
```

### 2. **Handler Classes** (handlers/)

#### **AuthHandler** - Xử lý authentication
```python
class AuthHandler:
    - handle_register(fd, data)   # 0x0001 REGISTER
    - handle_login(fd, data)      # 0x0002 LOGIN
```

#### **MatchmakingHandler** - Xử lý matchmaking
```python
class MatchmakingHandler:
    - handle_find_match(fd, data)         # 0x0010 FIND_MATCH
    - handle_cancel_find_match(fd, data)  # 0x0011 CANCEL_FIND_MATCH
    - handle_find_ai_match(fd, data)      # 0x0012 FIND_AI_MATCH
    
    State:
    - matchmaking_queue: []
    - active_games: {}
```

#### **GameHandler** - Xử lý game logic
```python
class GameHandler:
    - handle_make_move(fd, data)      # 0x0020 MAKE_MOVE
    - handle_resign(fd, data)         # 0x0021 RESIGN
    - handle_offer_draw(fd, data)     # 0x0022 OFFER_DRAW
    - handle_accept_draw(fd, data)    # 0x0023 ACCEPT_DRAW
    - handle_decline_draw(fd, data)   # 0x0024 DECLINE_DRAW
```

#### **StatsHandler** - Xử lý stats & history
```python
class StatsHandler:
    - handle_get_stats(fd, data)      # 0x0030 GET_STATS
    - handle_get_history(fd, data)    # 0x0031 GET_HISTORY
    - handle_get_replay(fd, data)     # 0x0032 GET_REPLAY
```

### 3. **NetworkManager** (tcp_server/network_bridge.py)
Low-level network layer (chỉ lo gửi/nhận):
- TCP socket management
- Message framing & parsing
- Event processing
- Handler registry
- **KHÔNG chứa business logic**

## 🎯 Separation of Concerns

### tcp_server/ - Network Layer ONLY
```
tcp_server/
├── protocol.h          # Protocol definitions (C)
├── server_core.c       # TCP server with poll() (C)
├── network_bridge.py   # NetworkManager (Python wrapper)
├── test_client.py      # Test utilities
└── Makefile            # Build system
```
**Chỉ chứa**: Socket, TCP, poll(), message framing, ctypes binding

### handlers/ - Business Logic ONLY
```
handlers/
├── auth_handler.py         # Login, Register
├── game_handler.py         # Move, Resign, Draw
├── matchmaking_handler.py  # Find match, AI game
└── stats_handler.py        # Stats, History, Replay
```
**Chỉ chứa**: Game rules, authentication, matchmaking logic

### Lợi ích của separation:
- ✅ Network code có thể reuse cho project khác
- ✅ Business logic không phụ thuộc vào TCP implementation
- ✅ Test network layer và business logic riêng biệt
- ✅ Dễ thay đổi protocol (TCP → WebSocket) mà không sửa handlers

## 🚀 Cách chạy

### Chạy với OOP architecture (Recommended):
```bash
cd back-end
python3 run_server.py
```

### Hoặc chạy trực tiếp:
```bash
cd back-end
python3 tcp_server/chess_server.py
```

### Chạy legacy version (monolithic):
```bash
cd back-end
python3 tcp_server/network_bridge.py  # Old monolithic version
```

## 📂 File Organization Principles

### ✅ tcp_server/ chứa gì?
- **Protocol definitions** (protocol.h)
- **C TCP implementation** (server_core.c)
- **Python wrapper** (network_bridge.py)
- **Build tools** (Makefile)
- **Test clients** (test_client.py)
- **Documentation** về network protocol

### ❌ tcp_server/ KHÔNG chứa:
- Business logic
- Game rules
- Authentication logic
- Database operations
- Handler implementations

### ✅ handlers/ chứa gì?
- Handler classes cho từng feature
- Business logic
- Game state management
- Request validation
- Response formatting

### ❌ handlers/ KHÔNG chứa:
- Network code
- Socket operations
- Protocol parsing
- TCP connection management

## ✨ Ưu điểm của cấu trúc OOP

### 1. **Separation of Concerns**
- ✅ Mỗi handler class chỉ lo 1 nhóm chức năng
- ✅ NetworkManager chỉ lo network layer
- ✅ Services lo business logic
- ✅ Models lo data structure

### 2. **Maintainability**
- ✅ Dễ tìm bug (biết ngay handler nào có vấn đề)
- ✅ Dễ thêm feature mới (thêm method vào handler)
- ✅ Dễ modify logic (chỉ sửa 1 file nhỏ)

### 3. **Testability**
- ✅ Test từng handler riêng biệt
- ✅ Mock network layer dễ dàng
- ✅ Unit test cho từng chức năng

### 4. **Scalability**
- ✅ Thêm handler mới không ảnh hưởng code cũ
- ✅ Có thể tách handlers thành microservices sau này
- ✅ Dễ parallel development (nhiều người code cùng lúc)

## 📊 So sánh

| Aspect | Old (Monolithic) | New (OOP) |
|--------|------------------|-----------|
| File size | 1 file ~800 lines | 6 files ~150-200 lines each |
| Logic separation | ❌ All in one | ✅ Separated by layer |
| Network layer | ⚠️ Mixed with logic | ✅ Pure network code |
| Business logic | ⚠️ In tcp_server | ✅ In handlers/ |
| Testability | ⚠️ Hard | ✅ Easy |
| Maintainability | ⚠️ Medium | ✅ High |
| Code reuse | ❌ Low | ✅ High |
| Team collaboration | ⚠️ Conflicts | ✅ No conflicts |

## 🔄 Migration

### Từ legacy sang OOP:
```bash
# Old way
python3 tcp_server/network_bridge.py

# New way
python3 run_server.py
```

Cả 2 cách đều hoạt động giống nhau, nhưng OOP version có cấu trúc tốt hơn.

## 📝 Adding New Features

### Thêm message type mới:

1. **Thêm vào protocol.h** (nếu cần C side)
2. **Thêm vào MessageTypeC2S enum** trong network_bridge.py
3. **Tạo handler method** trong handler class phù hợp:
   ```python
   # Ví dụ thêm vào GameHandler
   def handle_new_feature(self, client_fd: int, data: dict):
       """0x0025 - NEW_FEATURE: Description"""
       print(f"New feature from fd={client_fd}")
       # ... logic here
   ```
4. **Register handler** trong ChessGameServer._register_handlers():
   ```python
   self.network.register_handler(
       MessageTypeC2S.NEW_FEATURE, 
       self.game_handler.handle_new_feature
   )
   ```

### Thêm handler class mới:

1. **Tạo file** `handlers/new_handler.py`
2. **Import** trong `handlers/__init__.py`
3. **Initialize** trong ChessGameServer.__init__()
4. **Register** handlers trong _register_handlers()

## 🐛 Debugging

### Log output structure:
```
🔐 Login attempt: username        # AuthHandler
🔍 Find match request             # MatchmakingHandler
♟️  Move from fd=X                # GameHandler
📊 Stats request                  # StatsHandler
```

### Handler-specific debugging:
```python
# Trong handler method
print(f"DEBUG [{self.__class__.__name__}]: {data}")
```

## 📚 Documentation

- [NetworkManager API](network_bridge.py) - Low-level network
- [ChessGameServer](chess_server.py) - Main server class
- [Handlers](handlers/) - Feature handlers
- [Services](../services/) - Business logic
- [Models](../models/) - Data models

## 🎯 Best Practices

1. **Handler methods** nên là stateless khi có thể
2. **State** (như matchmaking_queue) nên ở handler level, không global
3. **Database access** luôn thông qua services
4. **Error handling** trong mỗi handler method
5. **Logging** rõ ràng để dễ debug

## 🚦 Status

- ✅ Refactored to OOP architecture
- ✅ All 13 message types supported
- ✅ Database integration
- ✅ Backward compatible
- ✅ Production ready
