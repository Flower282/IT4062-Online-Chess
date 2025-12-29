# TCP Chess Server - Quick Reference

## 📋 Build Commands
```bash
cd back-end/tcp_server
make              # Build library
make clean        # Clean
make debug        # Build with debug symbols
```

## 🚀 Run Server
```bash
# Simple example
python3 tcp_server/network_bridge.py

# Full chess server
python3 server_tcp_example.py
```

## 🧪 Test Client
```bash
# Interactive mode
python3 tcp_server/test_client.py interactive

# Quick test
python3 tcp_server/test_client.py test

# Registration test
python3 tcp_server/test_client.py register
```

## 📡 Message Types Quick Reference

### Client → Server (C2S)
| Code   | Name              | Payload                                    |
|--------|-------------------|--------------------------------------------|
| 0x0001 | REGISTER          | {username, password, email}                |
| 0x0002 | LOGIN             | {username, password}                       |
| 0x0010 | FIND_MATCH        | {}                                         |
| 0x0011 | CANCEL_FIND_MATCH | {}                                         |
| 0x0012 | FIND_AI_MATCH     | {difficulty}                               |
| 0x0020 | MAKE_MOVE         | {from, to, promotion?}                     |
| 0x0021 | RESIGN            | {}                                         |
| 0x0022 | OFFER_DRAW        | {}                                         |
| 0x0023 | ACCEPT_DRAW       | {}                                         |
| 0x0024 | DECLINE_DRAW      | {}                                         |
| 0x0030 | GET_STATS         | {}                                         |
| 0x0031 | GET_HISTORY       | {}                                         |
| 0x0032 | GET_REPLAY        | {game_id}                                  |

### Server → Client (S2C)
| Code   | Name                  | Payload                                    |
|--------|-----------------------|--------------------------------------------|
| 0x1001 | REGISTER_RESULT       | {success, error?, user_id?}                |
| 0x1002 | LOGIN_RESULT          | {success, error?, user_id?, username?}     |
| 0x1003 | USER_STATUS_UPDATE    | {status}                                   |
| 0x1100 | MATCH_FOUND           | {opponent_username, opponent_rating, ...}  |
| 0x1101 | GAME_START            | {game_id, color, opponent, fen}            |
| 0x1200 | GAME_STATE_UPDATE     | {game_id, fen, move, is_check, ...}        |
| 0x1201 | INVALID_MOVE          | {error}                                    |
| 0x1202 | GAME_OVER             | {game_id, result, winner?}                 |
| 0x1203 | DRAW_OFFER_RECEIVED   | {game_id}                                  |
| 0x1204 | DRAW_OFFER_DECLINED   | {game_id}                                  |
| 0x1300 | STATS_RESPONSE        | {wins, losses, draws, rating, ...}         |
| 0x1301 | HISTORY_RESPONSE      | {games: [...]}                             |
| 0x1302 | REPLAY_DATA           | {game_id, moves: [...]}                    |

## 💻 Python API

### Basic Setup
```python
from tcp_server.network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C

manager = NetworkManager()

# Register handler
def handle_login(client_fd: int, data: dict):
    manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
        'success': True,
        'user_id': 123
    })

manager.register_handler(MessageTypeC2S.LOGIN, handle_login)

# Start server
manager.start(port=8765)
manager.run_forever()
```

### Send Message to Client
```python
manager.send_to_client(
    client_fd,
    MessageTypeS2C.GAME_STATE_UPDATE,
    {'fen': 'rnbqkbnr/...', 'move': {'from': 'e2', 'to': 'e4'}}
)
```

### Get Client Info
```python
session = manager.get_client_info(client_fd)
username = session.get('username')
```

### Update Session
```python
manager.update_client_session(client_fd, authenticated=True, username='player1')
```

## 🔧 C API (for advanced users)

### Initialize
```c
int server_init(int port);
```

### Poll Events
```c
int server_poll(int timeout_ms);
```

### Send Message
```c
int send_message(int client_fd, uint16_t message_id, 
                 const uint8_t* payload, uint32_t payload_length);
```

### Get Event
```c
NetworkEvent* get_next_event(void);
void free_event(NetworkEvent* event);
```

## 🐛 Debugging

### Enable Debug Build
```bash
make debug
gdb python3
(gdb) run tcp_server/network_bridge.py
```

### Check Server Status
```bash
# Check if port is listening
netstat -tlnp | grep 8765

# Test connection
telnet localhost 8765

# Monitor traffic
tcpdump -i lo port 8765 -X
```

### Common Issues

**"Library not found"**
```bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/tcp_server
```

**"Port already in use"**
```bash
sudo lsof -i :8765
kill -9 <PID>
```

**"Connection refused"**
- Check if server is running
- Check firewall rules
- Verify port number

## 📦 Message Format

### Wire Format
```
[2 bytes: Message ID (big-endian)]
[4 bytes: Payload Length (big-endian)]
[N bytes: JSON Payload (UTF-8)]
```

### Example: Login Request
```
Hex: 00 02 00 00 00 2A 7B 22 75 73 65 72 6E 61 6D 65 22 ...
     ^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^...
     ID    Length      Payload
```

## 🎯 Performance Tips

1. **Batch sends**: Queue multiple messages if possible
2. **Use binary for game state**: Consider Protocol Buffers for FEN
3. **Connection pooling**: Reuse connections
4. **Tune poll timeout**: Balance between latency and CPU
5. **Profile with perf**: `perf record -g python3 server.py`

## 📚 Documentation
- Full docs: [README.md](tcp_server/README.md)
- Implementation: [TCP_IMPLEMENTATION_SUMMARY.md](TCP_IMPLEMENTATION_SUMMARY.md)
- Protocol spec: [protocol.h](tcp_server/protocol.h)

## ✅ Checklist

- [ ] Build library successfully
- [ ] Run example server
- [ ] Test with client
- [ ] Register handlers for all message types
- [ ] Update front-end to use TCP
- [ ] Test authentication flow
- [ ] Test matchmaking
- [ ] Test game play
- [ ] Load testing
- [ ] Production deployment
