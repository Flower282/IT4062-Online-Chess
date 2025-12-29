# TCP Chess Server - Implementation Summary

## Tổng Quan Dự Án

Dự án này chuyển đổi hệ thống từ **Python WebSockets** sang **TCP Socket thuần** viết bằng **C**, sử dụng cơ chế **I/O Multiplexing** với hàm `poll()`. Thư viện C được biên dịch thành **shared object (.so)** để Python gọi thông qua **ctypes**.

## Cấu Trúc Thư Mục

```
back-end/
├── tcp_server/              # Thư mục TCP server mới
│   ├── protocol.h           # Định nghĩa protocol và struct
│   ├── server_core.c        # Logic server C với poll()
│   ├── network_bridge.py    # Python bridge qua ctypes
│   ├── test_client.py       # Client test
│   ├── Makefile             # Build system
│   └── README.md            # Documentation
├── server_tcp_example.py    # Ví dụ tích hợp đầy đủ
└── build_and_test.sh        # Script build và test
```

## Chi Tiết Các File

### 1. protocol.h - Định Nghĩa Protocol

**Chức năng:**
- Định nghĩa các message types (C2S và S2C)
- Struct cho message header (6 bytes: 2 bytes message ID + 4 bytes payload length)
- Struct cho client session
- Function declarations

**Message Types:**

#### Client to Server (C2S)
```c
typedef enum {
    MSG_C2S_REGISTER            = 0x0001,  // Đăng ký tài khoản
    MSG_C2S_LOGIN               = 0x0002,  // Đăng nhập
    MSG_C2S_FIND_MATCH          = 0x0010,  // Tìm trận đấu
    MSG_C2S_CANCEL_FIND_MATCH   = 0x0011,  // Hủy tìm trận
    MSG_C2S_FIND_AI_MATCH       = 0x0012,  // Chơi với AI
    MSG_C2S_MAKE_MOVE           = 0x0020,  // Đi nước cờ
    MSG_C2S_RESIGN              = 0x0021,  // Đầu hàng
    MSG_C2S_OFFER_DRAW          = 0x0022,  // Đề nghị hòa
    MSG_C2S_ACCEPT_DRAW         = 0x0023,  // Chấp nhận hòa
    MSG_C2S_DECLINE_DRAW        = 0x0024,  // Từ chối hòa
    MSG_C2S_GET_STATS           = 0x0030,  // Xem thống kê
    MSG_C2S_GET_HISTORY         = 0x0031,  // Xem lịch sử
    MSG_C2S_GET_REPLAY          = 0x0032   // Xem replay
} MessageTypeC2S;
```

#### Server to Client (S2C)
```c
typedef enum {
    MSG_S2C_REGISTER_RESULT     = 0x1001,  // Kết quả đăng ký
    MSG_S2C_LOGIN_RESULT        = 0x1002,  // Kết quả đăng nhập
    MSG_S2C_USER_STATUS_UPDATE  = 0x1003,  // Cập nhật trạng thái
    MSG_S2C_MATCH_FOUND         = 0x1100,  // Tìm thấy trận đấu
    MSG_S2C_GAME_START          = 0x1101,  // Bắt đầu game
    MSG_S2C_GAME_STATE_UPDATE   = 0x1200,  // Cập nhật trạng thái game
    MSG_S2C_INVALID_MOVE        = 0x1201,  // Nước đi không hợp lệ
    MSG_S2C_GAME_OVER           = 0x1202,  // Kết thúc game
    MSG_S2C_DRAW_OFFER_RECEIVED = 0x1203,  // Nhận đề nghị hòa
    MSG_S2C_DRAW_OFFER_DECLINED = 0x1204,  // Đề nghị hòa bị từ chối
    MSG_S2C_STATS_RESPONSE      = 0x1300,  // Kết quả thống kê
    MSG_S2C_HISTORY_RESPONSE    = 0x1301,  // Kết quả lịch sử
    MSG_S2C_REPLAY_DATA         = 0x1302   // Dữ liệu replay
} MessageTypeS2C;
```

**Header Structure:**
```c
typedef struct {
    uint16_t message_id;      // 2 bytes (network byte order)
    uint32_t payload_length;  // 4 bytes (network byte order)
} __attribute__((packed)) MessageHeader;
```

### 2. server_core.c - Logic Server C

**Chức năng chính:**

#### Quản lý kết nối với poll()
```c
int server_poll(int timeout_ms);  // Poll events với timeout
```

- Sử dụng `struct pollfd ufds[]` để theo dõi file descriptors
- Xử lý `POLLIN` cho kết nối mới và data từ client
- Xử lý `POLLHUP` khi client ngắt kết nối

#### Quản lý client
```c
ClientSession clients[MAX_CLIENTS];  // Mảng 1024 client sessions
```

- Mỗi client có buffer riêng (64KB send + 64KB recv)
- Tracking username, user_id, game_id
- State management (DISCONNECTED, CONNECTED, AUTHENTICATED, IN_GAME)

#### Message handling
```c
int send_message(int client_fd, uint16_t message_id, 
                 const uint8_t* payload, uint32_t payload_length);
NetworkEvent* get_next_event(void);
void free_event(NetworkEvent* event);
```

- Đóng gói header với network byte order
- Xử lý fragmentation (dính gói TCP)
- Event queue cho Python integration

#### Non-blocking I/O
- Tất cả socket đều non-blocking
- Xử lý `EWOULDBLOCK`/`EAGAIN` properly
- Buffer partial messages until complete

### 3. network_bridge.py - Python Interface

**Chức năng:**

#### NetworkManager Class
```python
class NetworkManager:
    def __init__(self, library_path=None)
    def start(self, port: int) -> bool
    def stop(self)
    def poll(self, timeout_ms: int = 100) -> int
    def process_events(self) -> bool
    def send_to_client(self, client_fd: int, message_type: int, data: dict) -> bool
    def register_handler(self, message_type: int, handler: Callable)
    def run_forever(self, poll_timeout_ms: int = 100)
```

#### Event Processing
- Tự động decode JSON payload
- Call registered handlers
- Manage client sessions trong Python dict

#### Example Usage
```python
manager = NetworkManager()

def handle_login(client_fd: int, data: dict):
    username = data.get('username')
    # Validate and respond
    manager.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, {
        'success': True,
        'user_id': 123
    })

manager.register_handler(MessageTypeC2S.LOGIN, handle_login)
manager.start(port=8765)
manager.run_forever()
```

### 4. Makefile - Build System

**Targets:**
```bash
make          # Build shared library
make debug    # Build with debug symbols
make clean    # Clean build artifacts
make install  # Install to /usr/local/lib
make help     # Show help
```

**Compilation:**
```makefile
gcc -Wall -Wextra -O2 -fPIC -std=c11 -shared -o libchess_server.so server_core.c
```

## Cách Sử Dụng

### Bước 1: Build
```bash
cd back-end
chmod +x build_and_test.sh
./build_and_test.sh
```

### Bước 2: Chạy Server

**Option A: Server example đơn giản**
```bash
python3 tcp_server/network_bridge.py
```

**Option B: Server example đầy đủ**
```bash
python3 server_tcp_example.py
```

### Bước 3: Test với Client

**Interactive mode:**
```bash
python3 tcp_server/test_client.py interactive
```

Các lệnh trong interactive mode:
```
> login testuser password123
> find_match
> move e2 e4
> resign
> quit
```

**Basic test:**
```bash
python3 tcp_server/test_client.py test
```

**Registration test:**
```bash
python3 tcp_server/test_client.py register
```

## Tích Hợp với Code Hiện Tại

### Thay thế SocketIO

**Trước (WebSocket):**
```python
from flask_socketio import SocketIO

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('login')
def handle_login(data):
    username = data['username']
    # ...
    emit('login_result', result)
```

**Sau (TCP):**
```python
from tcp_server.network_bridge import NetworkManager, MessageTypeC2S, MessageTypeS2C

network = NetworkManager()

def handle_login(client_fd: int, data: dict):
    username = data['username']
    # ...
    network.send_to_client(client_fd, MessageTypeS2C.LOGIN_RESULT, result)

network.register_handler(MessageTypeC2S.LOGIN, handle_login)
network.start(port=8765)
network.run_forever()
```

### Broadcast Messages

**Trước:**
```python
socketio.emit('game_update', data, room=game_id)
```

**Sau:**
```python
# Send to both players
network.send_to_client(player1_fd, MessageTypeS2C.GAME_STATE_UPDATE, data)
network.send_to_client(player2_fd, MessageTypeS2C.GAME_STATE_UPDATE, data)
```

## Protocol Format

### Message Format
```
+------------------+----------------------+------------------+
| Message ID       | Payload Length       | Payload (JSON)   |
| 2 bytes          | 4 bytes              | Variable         |
| Big-endian       | Big-endian           | UTF-8            |
+------------------+----------------------+------------------+
```

### Example: Login Message

**Client sends (C2S_LOGIN = 0x0002):**
```
Header: 00 02 00 00 00 2A
Payload: {"username": "player1", "password": "pass123"}
```

**Server responds (S2C_LOGIN_RESULT = 0x1002):**
```
Header: 10 02 00 00 00 3C
Payload: {"success": true, "user_id": 12345, "username": "player1"}
```

## Ưu Điểm So Với WebSocket

1. **Performance**: 
   - Không có overhead của WebSocket framing
   - Poll() rất hiệu quả cho I/O multiplexing
   - Zero-copy buffers trong C

2. **Control**:
   - Hoàn toàn kiểm soát protocol
   - Custom header format
   - Dễ dàng optimize

3. **Scalability**:
   - Hỗ trợ đến 1024 concurrent connections
   - Event queue để batch processing
   - Non-blocking I/O

4. **Learning**:
   - Hiểu rõ TCP/IP stack
   - Network programming với poll()
   - C-Python integration với ctypes

## Các Điểm Quan Trọng

### 1. Xử lý Dính Gói (Fragmentation)
Server buffer partial messages cho đến khi nhận đủ header + payload:
```c
while (client->recv_offset >= HEADER_SIZE) {
    MessageHeader* header = (MessageHeader*)client->recv_buffer;
    // Check if complete message available
    if (client->recv_offset < HEADER_SIZE + payload_length) {
        break; // Need more data
    }
    // Process complete message
}
```

### 2. Network Byte Order
Luôn dùng `htons()` và `ntohl()` để convert:
```c
header.message_id = htons(message_id);
header.payload_length = htonl(payload_length);
```

### 3. Non-blocking Sockets
Kiểm tra error codes:
```c
if (errno == EWOULDBLOCK || errno == EAGAIN) {
    // Not an error, just no data available
    return;
}
```

### 4. Memory Management
- C side: Fixed buffers, no dynamic allocation per message
- Python side: Automatic với ctypes
- Free events sau khi process: `free_event(event_ptr)`

## Testing

### Unit Test C Functions
```bash
gcc -DTEST -g server_core.c -o test_server
./test_server
```

### Load Testing
```bash
# Run 100 concurrent clients
for i in {1..100}; do
    python3 tcp_server/test_client.py test &
done
wait
```

### Memory Leak Check
```bash
valgrind --leak-check=full python3 tcp_server/network_bridge.py
```

## Troubleshooting

### Lỗi Build
```bash
# Install build tools
sudo apt-get install build-essential

# Check compiler
gcc --version
```

### Lỗi Runtime
```bash
# Check library path
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/tcp_server

# Debug với strace
strace -e trace=network python3 tcp_server/network_bridge.py
```

### Port Already in Use
```bash
# Find process using port
sudo lsof -i :8765

# Kill process
kill -9 <PID>
```

## Kết Luận

Hệ thống TCP server với poll() đã được implement đầy đủ với:

✅ Protocol definition với message types
✅ C server core sử dụng poll() I/O multiplexing
✅ Python bridge qua ctypes
✅ Build system với Makefile
✅ Documentation đầy đủ
✅ Test client và example
✅ Integration example

Có thể bắt đầu migrate từ WebSocket sang TCP bằng cách:
1. Build library: `make`
2. Test với example: `python3 tcp_server/network_bridge.py`
3. Update server.py theo pattern trong `server_tcp_example.py`
4. Update front-end client để dùng TCP thay vì WebSocket
