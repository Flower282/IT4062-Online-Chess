# TCP Chess Server Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CHESS CLIENTS                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Player 1 │  │ Player 2 │  │ Player 3 │  │ Player N │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        │ TCP         │ TCP         │ TCP         │ TCP
        │ Socket      │ Socket      │ Socket      │ Socket
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    C TCP SERVER (server_core.c)                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   poll() I/O Multiplexing                  │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │ pollfd[0]│  │ pollfd[1]│  │ pollfd[2]│  │ pollfd[N]│  │ │
│  │  │ Listener │  │  Client  │  │  Client  │  │  Client  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Client Session Management                     │ │
│  │  ClientSession clients[MAX_CLIENTS]                        │ │
│  │  - fd, state, buffers, username, game_id                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Message Processing                            │ │
│  │  - Parse headers (6 bytes)                                 │ │
│  │  - Handle fragmentation                                    │ │
│  │  - Enqueue events                                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Event Queue                                   │ │
│  │  NetworkEvent event_queue[1024]                            │ │
│  │  - NEW_CONNECTION                                          │ │
│  │  - MESSAGE_RECEIVED                                        │ │
│  │  - CLIENT_DISCONNECTED                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                      │
                      │ ctypes (libchess_server.so)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              PYTHON BRIDGE (network_bridge.py)                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               NetworkManager Class                         │ │
│  │  - Load C library via ctypes                               │ │
│  │  - Event processing loop                                   │ │
│  │  - JSON serialization/deserialization                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Message Handler Registry                     │ │
│  │  handlers = {                                              │ │
│  │    MSG_C2S_LOGIN: handle_login,                            │ │
│  │    MSG_C2S_MAKE_MOVE: handle_move,                         │ │
│  │    ...                                                     │ │
│  │  }                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Client Session Tracking (Python)             │ │
│  │  client_sessions = {                                       │ │
│  │    fd: {username, user_id, game_id, ...}                   │ │
│  │  }                                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                      │
                      │ Function Calls
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              CHESS GAME LOGIC (Python)                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Authentication                               │ │
│  │  - User login/registration                                 │ │
│  │  - Database validation                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Matchmaking                                  │ │
│  │  - Queue management                                        │ │
│  │  - Player pairing                                          │ │
│  │  - Rating-based matching                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Game Management                              │ │
│  │  - Chess board state (python-chess)                        │ │
│  │  - Move validation                                         │ │
│  │  - Game end detection                                      │ │
│  │  - AI opponent (minimax/stockfish)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Database                                     │ │
│  │  - User accounts                                           │ │
│  │  - Game history                                            │ │
│  │  - Statistics                                              │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Message Flow Example: Player Login

```
Client                  C Server              Python Bridge         Game Logic
  │                        │                        │                    │
  │  1. TCP Connect        │                        │                    │
  │───────────────────────>│                        │                    │
  │                        │  2. NEW_CONNECTION     │                    │
  │                        │───────────────────────>│                    │
  │                        │                        │  3. Session Init   │
  │                        │                        │───────────────────>│
  │                        │                        │                    │
  │  4. LOGIN (0x0002)     │                        │                    │
  │  {username, password}  │                        │                    │
  │───────────────────────>│                        │                    │
  │                        │  5. MESSAGE_RECEIVED   │                    │
  │                        │  (0x0002, payload)     │                    │
  │                        │───────────────────────>│                    │
  │                        │                        │  6. handle_login() │
  │                        │                        │───────────────────>│
  │                        │                        │                    │
  │                        │                        │  7. DB Validate    │
  │                        │                        │<───────────────────│
  │                        │                        │                    │
  │                        │  8. send_to_client()   │                    │
  │                        │  LOGIN_RESULT (0x1002) │                    │
  │                        │<───────────────────────│                    │
  │  9. LOGIN_RESULT       │                        │                    │
  │  {success: true, ...}  │                        │                    │
  │<───────────────────────│                        │                    │
```

## Data Flow: Message Processing

```
┌──────────────────────────────────────────────────────────────┐
│                      TCP Stream                               │
│  [Raw bytes from socket...]                                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  Receive Buffer (C)                           │
│  client->recv_buffer[BUFFER_SIZE]                             │
│  client->recv_offset                                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               Header Parsing (C)                              │
│  MessageHeader (6 bytes)                                      │
│  ┌──────────────┬────────────────────────┐                   │
│  │ message_id   │ payload_length         │                   │
│  │ (2 bytes)    │ (4 bytes)              │                   │
│  └──────────────┴────────────────────────┘                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│            Fragmentation Handling (C)                         │
│  Wait until: recv_offset >= HEADER_SIZE + payload_length     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                Event Enqueue (C)                              │
│  NetworkEvent {                                               │
│    type: MESSAGE_RECEIVED,                                    │
│    client_fd: fd,                                             │
│    message_id: 0x0002,                                        │
│    payload_length: len,                                       │
│    payload_data: malloc(len)                                  │
│  }                                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Event Processing (Python)                        │
│  event = get_next_event()                                     │
│  payload_bytes = bytes(event.payload_data[:event.length])     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              JSON Deserialization (Python)                    │
│  payload_str = payload_bytes.decode('utf-8')                  │
│  data = json.loads(payload_str)                               │
│  # data = {'username': 'player1', 'password': '...'}          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Handler Dispatch (Python)                        │
│  handler = handlers[event.message_id]                         │
│  handler(event.client_fd, data)                               │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Business Logic (Python)                          │
│  def handle_login(client_fd, data):                           │
│      # Validate credentials                                   │
│      # Update session                                         │
│      # Send response                                          │
└───────────────────────────────────────────────────────────────┘
```

## Memory Layout

### C Server Memory
```
┌───────────────────────────────────────────────────────────┐
│  Stack                                                     │
│  - Local variables                                         │
│  - Function call frames                                    │
├───────────────────────────────────────────────────────────┤
│  Heap                                                      │
│  - Event payloads (malloc/free)                            │
├───────────────────────────────────────────────────────────┤
│  Data Segment (Global)                                     │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  int listener_fd                                     │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │  struct pollfd ufds[MAX_CLIENTS + 1]                │  │
│  │  - 8 bytes × 1025 = 8200 bytes                      │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │  ClientSession clients[MAX_CLIENTS]                 │  │
│  │  - 131,160 bytes × 1024 = ~128 MB                   │  │
│  │    (Most efficient for O(1) lookups)                │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │  NetworkEvent event_queue[1024]                     │  │
│  │  - 24 bytes × 1024 = 24,576 bytes                   │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### ClientSession Structure (per client)
```
struct ClientSession {
    int fd;                          // 4 bytes
    ClientState state;               // 4 bytes
    uint8_t recv_buffer[65536];     // 64 KB
    size_t recv_offset;              // 8 bytes
    uint8_t send_buffer[65536];     // 64 KB
    size_t send_offset;              // 8 bytes
    size_t send_length;              // 8 bytes
    char username[64];               // 64 bytes
    uint32_t user_id;                // 4 bytes
    int game_id;                     // 4 bytes
}; // Total: ~131 KB per client
```

## Performance Characteristics

### Time Complexity
- **Accept connection**: O(1)
- **Find client by fd**: O(n) worst case, O(1) average with array
- **Send message**: O(1)
- **Poll events**: O(n) where n = number of active fds
- **Process events**: O(m) where m = number of pending events

### Space Complexity
- **Per client**: ~131 KB (fixed buffers)
- **Total for 1024 clients**: ~128 MB
- **Event queue**: 24 KB

### Network Performance
- **Latency**: ~1ms (local network)
- **Throughput**: Limited by JSON serialization (~100K msg/sec)
- **Connections**: Up to 1024 concurrent clients

## Scalability Considerations

### Current Design (Single Process)
```
            Clients (1-1024)
                  │
                  ▼
          ┌───────────────┐
          │  C Server     │
          │  poll()       │
          └───────────────┘
                  │
                  ▼
          ┌───────────────┐
          │ Python Logic  │
          └───────────────┘
```

### Future: Multi-Process (>1024 clients)
```
        Clients (thousands)
               │
               ▼
       ┌──────────────┐
       │ Load Balancer│
       └──────────────┘
          │    │    │
    ┌─────┘    │    └─────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│Worker 1│ │Worker 2│ │Worker N│
└────────┘ └────────┘ └────────┘
    │          │          │
    └──────────┴──────────┘
               │
               ▼
       ┌──────────────┐
       │   Database   │
       └──────────────┘
```

## Security Considerations

### Current Implementation
- ❌ No TLS/SSL (plaintext)
- ✅ Fixed buffer sizes (no buffer overflow)
- ✅ Input validation on message parsing
- ❌ No rate limiting
- ❌ No authentication token refresh

### Recommended Additions
1. **TLS wrapper**: OpenSSL/mbedtls
2. **Rate limiting**: Token bucket per client
3. **Message size limits**: Already enforced (64KB)
4. **Connection timeout**: Idle connection cleanup
5. **DDoS protection**: SYN flood protection at OS level
