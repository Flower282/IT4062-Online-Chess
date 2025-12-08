## Cài đặt các dependencies

```bash
pip3 install -r requirements.txt
```

## Chạy server

### Chạy trên port mặc định (8080)

```bash
python3 server.py
```

### Chạy trên port tùy chỉnh

```bash
PORT=3000 python3 server.py
```

Server sẽ khởi động và lắng nghe kết nối từ client.

## Cấu trúc project

```
back-end/
├── server.py           # File chính của server
├── engine.py           # Chess engine logic
├── requirements.txt    # Python dependencies
├── environment.yml     # Conda environment config
├── Procfile           # Heroku deployment config
├── minimax/           # Thuật toán minimax cho AI
│   ├── evaluate.py    # Hàm đánh giá vị trí
│   ├── ordermoves.py  # Sắp xếp nước đi
│   └── search.py      # Thuật toán tìm kiếm
├── ml/                # Machine Learning models
│   ├── filter.py      # Lọc nước đi
│   └── trained_model/ # Mô hình đã huấn luyện
└── stockfish/         # Stockfish chess engine
```

## Tính năng

- **Multiplayer**: Chơi với người chơi khác qua mạng
- **AI Engine**: Chơi với máy tính (Minimax + Machine Learning)
- **Stockfish Integration**: Tích hợp Stockfish engine mạnh mẽ
- **Real-time Communication**: Sử dụng Socket.IO cho giao tiếp thời gian thực

## API Endpoints

Server sử dụng Socket.IO với các events:

- `connect`: Kết nối client
- `create`: Tạo game mới
- `join`: Tham gia game
- `move`: Thực hiện nước đi
- `disconnect`: Ngắt kết nối
