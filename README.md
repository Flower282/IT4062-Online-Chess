# IT4062-Online-Chess

Online Chess Game with Desktop Client and TCP Server

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MongoDB
- GCC compiler (for C server)
- PyQt6

### Backend Setup

1. Navigate to backend directory:
```bash
cd back-end
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure MongoDB:
- Copy `.env.example` to `.env`
- Update MongoDB connection string in `.env`

4. Compile C server:
```bash
cd tcp_server
make
cd ..
```

5. Run the server:
```bash
python3 run_server.py
```

Server will start on `localhost:8765`

### Desktop Client Setup

1. Navigate to desktop app directory:
```bash
cd desktop-app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python3 main.py
```

## 👤 Demo Accounts

For testing purposes, use these pre-configured accounts:

| Email | Password |
|-------|----------|
| user1@exam.com | 12345678 |
| user2@exam.com | 12345678 |

**Note**: Make sure to create these accounts in the database or register them through the app before first use.

## 🎮 Features

### Desktop Client
- **Login/Register**: User authentication with MongoDB
- **Game Lobby**: Find opponents or play against AI
- **Live Chess Game**: Real-time chess gameplay with move validation
- **Game History**: View past games and replay moves
- **Player Stats**: ELO rating system

### Backend
- **TCP Server**: Custom binary protocol for efficient communication
- **MongoDB Integration**: User management and game persistence
- **Move Validation**: Server-side chess rule enforcement
- **Matchmaking**: PvP and AI opponent matching
- **ELO Rating**: Chess rating calculation (K-factor=32)

### Network Protocol
- **Transport**: TCP with binary protocol
- **Header**: 6 bytes (2B message_id + 4B payload_length)
- **Payload**: JSON-encoded game data
- **Messages**: 13 C2S + 12 S2C message types

### Database Schema
- **Users**: email, password (bcrypt), elo_rating, games_played
- **Games**: white_player, black_player, moves (PGN), result, timestamps

## 🛠️ Development

### Running Tests
```bash
cd back-end/tcp_server
python3 test_client.py
```

