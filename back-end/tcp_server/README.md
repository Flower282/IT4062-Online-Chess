# TCP Server Migration Guide

## Overview
This directory contains the C TCP server implementation with custom protocol, replacing the previous Python WebSocket implementation.

## Architecture

### Components

1. **protocol.h** - Protocol definitions
   - Message type enums (C2S and S2C)
   - Fixed header structure (6 bytes: 2-byte message ID + 4-byte payload length)
   - Client session structures
   - Function declarations

2. **server_core.c** - Core server implementation
   - TCP socket server with `poll()` for I/O multiplexing
   - Client connection management (up to 1024 concurrent clients)
   - Message framing and fragmentation handling
   - Event queue for Python integration

3. **network_bridge.py** - Python interface
   - `ctypes` wrapper for C library
   - Event processing loop
   - Message handler registration system
   - Session management

4. **Makefile** - Build system
   - Compiles C code to shared library (.so)
   - Debug and release builds
   - Installation targets

## Message Protocol

### Header Format (6 bytes)
```
+------------------+----------------------+
| Message ID       | Payload Length       |
| (2 bytes)        | (4 bytes)            |
| uint16_t         | uint32_t             |
+------------------+----------------------+
```

- **Message ID**: Network byte order (big-endian)
- **Payload Length**: Network byte order (big-endian)
- **Payload**: JSON-encoded data (UTF-8)

### Message Types

#### Client to Server (C2S)
| Code   | Name                  | Description                    |
|--------|-----------------------|--------------------------------|
| 0x0001 | REGISTER              | Register new account           |
| 0x0002 | LOGIN                 | Login with credentials         |
| 0x0010 | FIND_MATCH            | Request matchmaking            |
| 0x0011 | CANCEL_FIND_MATCH     | Cancel matchmaking             |
| 0x0012 | FIND_AI_MATCH         | Request AI opponent            |
| 0x0020 | MAKE_MOVE             | Submit chess move              |
| 0x0021 | RESIGN                | Resign from game               |
| 0x0022 | OFFER_DRAW            | Offer draw to opponent         |
| 0x0023 | ACCEPT_DRAW           | Accept draw offer              |
| 0x0024 | DECLINE_DRAW          | Decline draw offer             |
| 0x0030 | GET_STATS             | Request user statistics        |
| 0x0031 | GET_HISTORY           | Request game history           |
| 0x0032 | GET_REPLAY            | Request game replay data       |

#### Server to Client (S2C)
| Code   | Name                  | Description                    |
|--------|-----------------------|--------------------------------|
| 0x1001 | REGISTER_RESULT       | Registration result            |
| 0x1002 | LOGIN_RESULT          | Login result                   |
| 0x1003 | USER_STATUS_UPDATE    | User status changed            |
| 0x1100 | MATCH_FOUND           | Match found notification       |
| 0x1101 | GAME_START            | Game started                   |
| 0x1200 | GAME_STATE_UPDATE     | Game state changed             |
| 0x1201 | INVALID_MOVE          | Invalid move submitted         |
| 0x1202 | GAME_OVER             | Game ended                     |
| 0x1203 | DRAW_OFFER_RECEIVED   | Draw offer from opponent       |
| 0x1204 | DRAW_OFFER_DECLINED   | Draw offer declined            |
| 0x1300 | STATS_RESPONSE        | User statistics                |
| 0x1301 | HISTORY_RESPONSE      | Game history                   |
| 0x1302 | REPLAY_DATA           | Game replay data               |

## Building

### Prerequisites
- GCC compiler with C11 support
- Python 3.7+
- Linux/Unix environment

### Compilation
```bash
cd tcp_server
make
```

This creates `libchess_server.so` in the current directory.

### Debug Build
```bash
make debug
```

### Clean
```bash
make clean
```

## Usage

### Basic Python Integration

```python
from network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C

# Create network manager
manager = NetworkManager()

# Define message handler
def handle_login(client_fd: int, data: dict):
    username = data.get('username')
    password = data.get('password')
    
    # Validate credentials
    if authenticate(username, password):
        manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
            'success': True,
            'user_id': 12345,
            'username': username
        })
    else:
        manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
            'success': False,
            'error': 'Invalid credentials'
        })

# Register handler
manager.register_handler(MessageTypeC2S.LOGIN, handle_login)

# Start server
if manager.start(port=8765):
    manager.run_forever()
```

### Advanced Usage - Custom Event Loop

```python
from network_bridge import NetworkManager

manager = NetworkManager()

# Register all handlers...
manager.register_handler(MessageTypeC2S.LOGIN, handle_login)
manager.register_handler(MessageTypeC2S.MAKE_MOVE, handle_move)
# ... etc

# Start server
manager.start(port=8765)

# Custom event loop
import time
while True:
    # Poll with 100ms timeout
    manager.poll(100)
    
    # Process all pending events
    manager.process_events()
    
    # Your custom logic here
    time.sleep(0.01)
```

## Integration with Existing Server

To integrate with your existing `server.py`:

1. Import the network bridge:
```python
from tcp_server.network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C
```

2. Replace SocketIO initialization with NetworkManager:
```python
# Old:
# socketio = SocketIO(app, cors_allowed_origins="*")

# New:
network_manager = NetworkManager()
```

3. Convert Socket.IO event handlers to message handlers:
```python
# Old:
@socketio.on('login')
def handle_login(data):
    # ...

# New:
def handle_login(client_fd: int, data: dict):
    # ...
    
network_manager.register_handler(MessageTypeC2S.LOGIN, handle_login)
```

4. Replace socketio.emit() with send_to_client():
```python
# Old:
socketio.emit('login_result', data, room=sid)

# New:
network_manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, data)
```

## Memory Management

### C Side
- Fixed-size buffers (64KB per client) to avoid dynamic allocation
- Event queue uses circular buffer
- Proper cleanup on client disconnect

### Python Side
- Event payloads are automatically freed after processing
- Session tracking in Python dictionary
- No manual memory management required

## Error Handling

### Network Errors
- `poll()` returns -1: Check `errno` and log error
- `recv()` returns 0: Client disconnected gracefully
- `recv()` returns -1: Check for `EWOULDBLOCK`/`EAGAIN` (non-fatal)

### Message Errors
- Incomplete header: Buffer until complete header received
- Incomplete payload: Buffer until complete message received
- Invalid JSON: Log error and skip message
- Unknown message type: Log warning

## Performance Considerations

1. **I/O Multiplexing**: Uses `poll()` to handle multiple clients efficiently
2. **Non-blocking I/O**: All sockets are non-blocking
3. **Zero-copy where possible**: Direct buffer manipulation
4. **Event batching**: Process all available events before returning to poll

## Testing

### Test Client (Python)
```python
import socket
import struct
import json

def send_message(sock, message_id, data):
    payload = json.dumps(data).encode('utf-8')
    header = struct.pack('!HI', message_id, len(payload))
    sock.sendall(header + payload)

def recv_message(sock):
    header = sock.recv(6)
    if len(header) < 6:
        return None
    message_id, payload_len = struct.unpack('!HI', header)
    payload = sock.recv(payload_len)
    data = json.loads(payload.decode('utf-8'))
    return message_id, data

# Connect
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 8765))

# Send login
send_message(sock, 0x0002, {'username': 'test', 'password': 'test123'})

# Receive response
msg_id, data = recv_message(sock)
print(f"Received: 0x{msg_id:04x} {data}")

sock.close()
```

### Load Testing
```bash
# Multiple concurrent connections
for i in {1..100}; do
    python3 test_client.py &
done
```

## Migration Checklist

- [x] Define protocol (message types and structures)
- [x] Implement C server core with poll()
- [x] Create Python bridge with ctypes
- [x] Create build system (Makefile)
- [ ] Update server.py to use NetworkManager
- [ ] Update client to use TCP protocol
- [ ] Test authentication flow
- [ ] Test matchmaking
- [ ] Test game play
- [ ] Load testing
- [ ] Deploy to production

## Troubleshooting

### Build Errors
- **Missing headers**: Install build-essential
- **Symbol not found**: Check function signatures match between .h and .c

### Runtime Errors
- **Library not found**: Add directory to LD_LIBRARY_PATH or use absolute path
- **Port already in use**: Check for existing processes or change port
- **Segmentation fault**: Check buffer bounds and null pointer access

### Connection Issues
- **Connection refused**: Ensure server is running and firewall allows port
- **Connection timeout**: Check network connectivity
- **Connection reset**: Client or server crashed

## Future Enhancements

1. **TLS/SSL Support**: Secure communication
2. **Binary Protocol**: More efficient than JSON for game state
3. **Compression**: Reduce bandwidth usage
4. **Heartbeat**: Detect dead connections
5. **Reconnection**: Resume session after disconnect
6. **Message Priority**: Prioritize game moves over stats
7. **Rate Limiting**: Prevent abuse
8. **Metrics**: Connection count, message rates, latency

## References

- [poll() man page](https://man7.org/linux/man-pages/man2/poll.2.html)
- [TCP Socket Programming in C](https://beej.us/guide/bgnet/)
- [Python ctypes Documentation](https://docs.python.org/3/library/ctypes.html)
