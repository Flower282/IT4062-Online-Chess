# Chess Desktop Application

PyQt6-based desktop chess application that connects to the C TCP server.

## Overview

This is a complete refactoring of the React web frontend to a native desktop application using PyQt6. It communicates with the C TCP server using the custom binary protocol.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Main Application                    │
│               (QStackedWidget)                       │
│  ┌──────────────────────────────────────────────┐  │
│  │  Login → Register → Lobby → Game             │  │
│  └──────────────────────────────────────────────┘  │
│                        ↓                             │
│               NetworkClient (QObject)                │
│                        ↓                             │
│          TCP Socket with Binary Protocol            │
│                        ↓                             │
│                  C TCP Server                        │
└─────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.8+
- PyQt6
- python-chess

### Setup

```bash
cd desktop-app

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Start the C TCP Server

First, make sure the C TCP server is running:

```bash
cd ../back-end/tcp_server
make
./test_server
```

The server will listen on `localhost:8765`.

### 2. Run the Desktop App

```bash
python main.py
```

## Features

### ✓ User Authentication
- **Login Window**: Email/password authentication with validation
- **Register Window**: New user registration with password confirmation
- Protocol: Uses `MSG_REGISTER (0x0001)`, `MSG_LOGIN (0x0002)`

### ✓ Game Lobby
- **Find Match**: Search for online opponents
- **Play vs AI**: Choose AI difficulty (Easy, Medium, Hard)
- **View Stats**: Display user statistics (wins, losses, rating)
- Protocol: `MSG_MATCHMAKING (0x0010)`, `MSG_PLAY_AI (0x0012)`

### ✓ Chess Game
- **Interactive Board**: Drag-and-drop piece movement
- **Move Validation**: Real-time validation through server
- **Game Controls**: Resign, offer draw, rematch
- **Move History**: Display all moves in standard notation
- **Timer Display**: Shows remaining time for both players
- Protocol: `MSG_MAKE_MOVE (0x0020)`, `MSG_RESIGN (0x0021)`, `MSG_OFFER_DRAW (0x0022)`

### ✓ Real-time Updates
- Async network communication using Qt Signals/Slots
- Non-blocking UI with worker thread for TCP socket
- Automatic reconnection on disconnect

## Component Mapping (React → PyQt6)

| React Component | PyQt6 Component | File |
|----------------|-----------------|------|
| `App.jsx` | `ChessApplication` | `main.py` |
| `Login.jsx` | `LoginWindow` | `login_window.py` |
| `Register.jsx` | `RegisterWindow` | `register_window.py` |
| `NewGamePopup.jsx` | `LobbyWindow` | `lobby_window.py` |
| `ChessBoard.jsx` | `GameWindow` + `ChessBoardWidget` | `game_window.py`, `chess_board_widget.py` |
| `SocketConfig.js` | `NetworkClient` | `network_client.py` |

## State Management

| React Pattern | PyQt6 Pattern |
|---------------|---------------|
| `useState` | Class member variables |
| `useEffect` | Qt Signals/Slots |
| `useContext` | Passed through constructor |
| Event handlers (`onClick`) | Signal connections |
| WebSocket | TCP Socket with worker thread |

## Network Protocol

The app uses the same binary protocol as defined in `protocol.h`:

### Message Structure
```
┌──────────────┬────────────────┬─────────────┐
│  Message ID  │ Payload Length │   Payload   │
│   (2 bytes)  │   (4 bytes)    │  (variable) │
└──────────────┴────────────────┴─────────────┘
```

### Client-to-Server Messages (C2S)
- `0x0001`: Register new user
- `0x0002`: Login
- `0x0010`: Start matchmaking
- `0x0011`: Cancel matchmaking
- `0x0012`: Play vs AI
- `0x0020`: Make move
- `0x0021`: Resign game
- `0x0022`: Offer draw
- `0x0023`: Accept draw
- `0x0024`: Decline draw
- `0x0030`: Request game state
- `0x0031`: Request user stats
- `0x0032`: Request game history

### Server-to-Client Messages (S2C)
- `0x1001`: Register response
- `0x1002`: Login response
- `0x1100`: Match found
- `0x1101`: Game started
- `0x1200`: Game state update
- `0x1201`: Invalid move
- `0x1202`: Game over
- `0x1300`: User stats response
- `0x1301`: Game history response
- `0x1302`: Error message

## Code Structure

### Main Application (`main.py`)
- `ChessApplication`: Main window using QStackedWidget for navigation
- Manages window transitions: Login → Register → Lobby → Game
- Handles network connection and user session

### Network Client (`network_client.py`)
- `NetworkClient`: TCP client with Qt integration
- Worker thread for non-blocking I/O
- Qt Signals for async updates:
  - `connected`: Connection established
  - `disconnected`: Connection lost
  - `message_received(int, dict)`: New message from server
  - `error_occurred(str)`: Network error

### UI Windows

#### Login Window (`login_window.py`)
- Email and password input fields
- Form validation
- Sends `MSG_LOGIN` to server
- Signals: `login_success(dict)`, `switch_to_register()`

#### Register Window (`register_window.py`)
- Username, email, password, confirm password fields
- Client-side validation (email format, password match)
- Sends `MSG_REGISTER` to server
- Signals: `register_success()`, `switch_to_login()`

#### Lobby Window (`lobby_window.py`)
- User info display (username, rating)
- Matchmaking panel with "Find Match" button
- AI game panel with difficulty selection
- User statistics display
- Signals: `start_game(dict)`, `logout_requested()`

#### Game Window (`game_window.py`)
- Chess board display
- Move history panel
- Game controls (Resign, Draw Offer, Rematch)
- Timer display for both players
- Signals: `quit_game()`

#### Chess Board Widget (`chess_board_widget.py`)
- 8×8 grid of squares
- Unicode chess pieces (♔♕♖♗♘♙ / ♚♛♜♝♞♟)
- Drag-and-drop piece movement
- Visual feedback (selected square, legal moves)
- Signals: `move_made(str, str)`

## Styling

The app uses Qt Style Sheets (QSS) to mimic the original React CSS:

```python
button.setStyleSheet("""
    QPushButton {
        background-color: #28a745;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #218838;
    }
""")
```

## Development

### Adding New Features

1. **Add Protocol Message**: Define in `../back-end/tcp_server/protocol.h`
2. **Update Network Client**: Add method in `network_client.py`
3. **Handle in UI**: Connect signal in appropriate window
4. **Update Server**: Implement handler in C server

### Debugging

Enable debug output:
```python
# In network_client.py
DEBUG = True  # Set to True for verbose logging
```

### Testing

Test individual components:
```bash
# Test network client
python network_client.py

# Test windows
python login_window.py
python chess_board_widget.py
```

## Comparison: React vs PyQt6

### Advantages of Desktop App
- ✓ Native OS integration
- ✓ Better performance (no browser overhead)
- ✓ Direct TCP communication (no WebSocket)
- ✓ Offline installation
- ✓ System tray integration possible
- ✓ Native notifications

### Disadvantages
- ✗ Requires installation
- ✗ Platform-specific builds needed
- ✗ Larger distribution size
- ✗ Update distribution more complex

## Troubleshooting

### Connection Failed
- Ensure C TCP server is running on `localhost:8765`
- Check firewall settings
- Verify network client host/port settings

### UI Not Responding
- Check console for error messages
- Ensure network operations are in worker thread
- Verify signal/slot connections

### Import Errors
- Install all dependencies: `pip install -r requirements.txt`
- Use Python 3.8 or higher
- Consider using virtual environment

## Future Enhancements

- [ ] Connection settings dialog (configure host/port)
- [ ] Theme selection (light/dark mode)
- [ ] Sound effects for moves
- [ ] Board themes (different piece styles)
- [ ] Analysis mode (engine evaluation)
- [ ] Game export to PGN
- [ ] Friend list and challenges
- [ ] Chat system
- [ ] Tournament support

## License

Same as parent project.

## Credits

Refactored from React web app to PyQt6 desktop app by IT4062 team.
