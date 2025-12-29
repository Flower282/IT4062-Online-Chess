"""
Game Window - PyQt6
Main game interface with chess board and controls
Replaces React ChessBoard.jsx component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFrame, QMessageBox,
                            QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from chess_board_widget import ChessBoardWidget
from network_client import MessageTypeS2C
import chess


class GameWindow(QWidget):
    """
    Game window with chess board and controls
    
    React state mapping:
    - useState(game) -> self.game_data
    - useState(orientation) -> self.orientation
    - useState(disconnected) -> self.is_disconnected
    - useState(resigned) -> self.is_resigned
    
    React events:
    - socket.on('fetch') -> MSG_S2C_GAME_STATE_UPDATE (0x1200)
    - socket.on('disconnected') -> Handle disconnection
    - socket.on('resigned') -> MSG_S2C_GAME_OVER (0x1202)
    """
    
    # Signals
    quit_game = pyqtSignal()  # Back to lobby
    
    def __init__(self, network_client, game_data, user_data, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.game_data = game_data
        self.user_data = user_data
        self.is_disconnected = False
        self.is_resigned = False
        self.opponent_resigned = False
        
        # Store game_id for requests
        self.game_id = game_data.get('game_id', '')
        
        # Determine player color
        self.my_color = game_data.get('color', 'white')
        self.opponent_name = game_data.get('opponent', 'Unknown')
        
        self.init_ui()
        self.setup_network_handlers()
    
    def init_ui(self):
        """Initialize game UI"""
        self.setWindowTitle("Chess Game")
        self.setMinimumSize(900, 700)
        
        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        
        # Left side - Move history and info
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Center - Chess board
        board_container = self.create_board_container()
        main_layout.addWidget(board_container, 2)
        
        # Right side - Controls
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        self.setLayout(main_layout)
        self.setStyleSheet("QWidget { background-color: #f5f5f5; }")
    
    def create_left_panel(self):
        """Create left panel with move history"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Move History")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Opponent info
        opponent_frame = QFrame()
        opponent_frame.setStyleSheet("background-color: #333; border-radius: 4px; padding: 10px;")
        opponent_layout = QVBoxLayout(opponent_frame)
        
        self.opponent_label = QLabel(self.opponent_name)
        self.opponent_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.opponent_label.setStyleSheet("color: white;")
        self.opponent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opponent_layout.addWidget(self.opponent_label)
        
        self.opponent_color_label = QLabel(f"Playing as: {'Black' if self.my_color == 'white' else 'White'}")
        self.opponent_color_label.setStyleSheet("color: #aaa;")
        self.opponent_color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opponent_layout.addWidget(self.opponent_color_label)
        
        layout.addWidget(opponent_frame)
        
        # Move history text area
        self.move_history = QTextEdit()
        self.move_history.setReadOnly(True)
        self.move_history.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.move_history)
        
        # Player info (you)
        player_frame = QFrame()
        player_frame.setStyleSheet("background-color: #2196f3; border-radius: 4px; padding: 10px;")
        player_layout = QVBoxLayout(player_frame)
        
        self.player_label = QLabel(self.user_data.get('username', 'You'))
        self.player_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.player_label.setStyleSheet("color: white;")
        self.player_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(self.player_label)
        
        self.player_color_label = QLabel(f"Playing as: {self.my_color.capitalize()}")
        self.player_color_label.setStyleSheet("color: #e3f2fd;")
        self.player_color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(self.player_color_label)
        
        layout.addWidget(player_frame)
        
        return panel
    
    def create_board_container(self):
        """Create chess board container"""
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.StyledPanel)
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #333;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Game status label
        self.status_label = QLabel("Your turn" if self.my_color == 'white' else "Opponent's turn")
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #2196f3; padding: 10px;")
        layout.addWidget(self.status_label)
        
        # Chess board widget
        self.chess_board = ChessBoardWidget(orientation=self.my_color)
        self.chess_board.move_made.connect(self.on_move_made)
        
        # Set initial position from game data
        fen = self.game_data.get('fen', chess.STARTING_FEN)
        self.chess_board.set_board(fen)
        
        layout.addWidget(self.chess_board)
        
        return container
    
    def create_right_panel(self):
        """Create right panel with game controls"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Game Controls")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Offer Draw button - sends MSG_C2S_OFFER_DRAW (0x0022)
        self.draw_button = QPushButton("🤝 Offer Draw")
        self.draw_button.setMinimumHeight(40)
        self.draw_button.setFont(QFont("Arial", 11))
        self.draw_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.draw_button.clicked.connect(self.on_offer_draw)
        layout.addWidget(self.draw_button)
        
        # Resign button - sends MSG_C2S_RESIGN (0x0021)
        self.resign_button = QPushButton("🏳 Resign")
        self.resign_button.setMinimumHeight(40)
        self.resign_button.setFont(QFont("Arial", 11))
        self.resign_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.resign_button.clicked.connect(self.on_resign)
        layout.addWidget(self.resign_button)
        
        # Game info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        
        game_id_label = QLabel(f"Game ID: {self.game_data.get('game_id', 'N/A')}")
        game_id_label.setFont(QFont("Arial", 9))
        game_id_label.setStyleSheet("color: #666;")
        info_layout.addWidget(game_id_label)
        
        layout.addWidget(info_frame)
        
        layout.addStretch()
        
        # Quit button
        self.quit_button = QPushButton("⬅ Back to Lobby")
        self.quit_button.setMinimumHeight(40)
        self.quit_button.setFont(QFont("Arial", 11))
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        self.quit_button.clicked.connect(self.confirm_quit)
        layout.addWidget(self.quit_button)
        
        return panel
    
    def setup_network_handlers(self):
        """Setup network message handlers"""
        self.network.message_received.connect(self.on_message_received)
    
    def on_message_received(self, message_id: int, data: dict):
        """Handle incoming network messages"""
        if message_id == MessageTypeS2C.GAME_STATE_UPDATE:
            self.handle_game_state_update(data)
        elif message_id == MessageTypeS2C.INVALID_MOVE:
            self.handle_invalid_move(data)
        elif message_id == MessageTypeS2C.GAME_OVER:
            self.handle_game_over(data)
        elif message_id == MessageTypeS2C.DRAW_OFFER_RECEIVED:
            self.handle_draw_offer_received(data)
        elif message_id == MessageTypeS2C.DRAW_OFFER_DECLINED:
            self.handle_draw_offer_declined(data)
    
    def on_move_made(self, from_square: str, to_square: str):
        """
        Handle move made on board
        Sends MSG_C2S_MAKE_MOVE (0x0020)
        """
        # Send move to server with game_id
        self.network.make_move(self.game_id, from_square, to_square)
        
        # Update status
        self.status_label.setText("Waiting for server...")
    
    def handle_game_state_update(self, data: dict):
        """
        Handle game state update from server
        Receives MSG_S2C_GAME_STATE_UPDATE (0x1200)
        """
        # Update board
        fen = data.get('fen')
        if fen:
            self.chess_board.set_board(fen)
        
        # Update move history
        move = data.get('move', {})
        if move:
            move_text = f"{move.get('from')} → {move.get('to')}"
            self.move_history.append(move_text)
        
        # Update status
        board = chess.Board(fen)
        if board.turn == (chess.WHITE if self.my_color == 'white' else chess.BLACK):
            self.status_label.setText("Your turn")
            self.status_label.setStyleSheet("color: #4caf50; padding: 10px; font-weight: bold;")
        else:
            self.status_label.setText("Opponent's turn")
            self.status_label.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        
        # Check for check
        if data.get('is_check'):
            self.status_label.setText(self.status_label.text() + " - CHECK!")
        
        # Check for game over
        if data.get('game_over'):
            self.handle_game_over(data)
    
    def handle_invalid_move(self, data: dict):
        """
        Handle invalid move error
        Receives MSG_S2C_INVALID_MOVE (0x1201)
        """
        error = data.get('error', 'Invalid move')
        QMessageBox.warning(self, "Invalid Move", error)
        
        # Reset status
        board = chess.Board(self.chess_board.get_fen())
        if board.turn == (chess.WHITE if self.my_color == 'white' else chess.BLACK):
            self.status_label.setText("Your turn")
        else:
            self.status_label.setText("Opponent's turn")
    
    def handle_game_over(self, data: dict):
        """
        Handle game over
        Receives MSG_S2C_GAME_OVER (0x1202)
        """
        result = data.get('result', 'unknown')
        winner = data.get('winner', None)
        
        # Determine message
        if result == 'checkmate':
            if winner == self.my_color:
                message = "Checkmate! You won! 🎉"
                title = "Victory"
            else:
                message = "Checkmate! You lost."
                title = "Defeat"
        elif result == 'resignation':
            if winner == self.my_color:
                message = "Opponent resigned. You won! 🎉"
                title = "Victory"
            else:
                message = "You resigned."
                title = "Resigned"
        elif result == 'draw_agreement':
            message = "Game drawn by agreement."
            title = "Draw"
        elif result == 'stalemate':
            message = "Stalemate! Game drawn."
            title = "Draw"
        else:
            message = f"Game over: {result}"
            title = "Game Over"
        
        # Show message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        
        # Return to lobby
        self.quit_game.emit()
    
    def on_offer_draw(self):
        """
        Handle offer draw button
        Sends MSG_C2S_OFFER_DRAW (0x0022)
        """
        reply = QMessageBox.question(self, "Offer Draw",
                                    "Do you want to offer a draw to your opponent?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.network.offer_draw(self.game_id)
            QMessageBox.information(self, "Draw Offer", "Draw offer sent to opponent.")
    
    def handle_draw_offer_received(self, data: dict):
        """
        Handle draw offer from opponent
        Receives MSG_S2C_DRAW_OFFER_RECEIVED (0x1203)
        """
        reply = QMessageBox.question(self, "Draw Offer",
                                    "Your opponent offers a draw. Do you accept?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Send MSG_C2S_ACCEPT_DRAW (0x0023)
            self.network.accept_draw()
        else:
            # Send MSG_C2S_DECLINE_DRAW (0x0024)
            self.network.decline_draw()
    
    def handle_draw_offer_declined(self, data: dict):
        """
        Handle draw offer declined
        Receives MSG_S2C_DRAW_OFFER_DECLINED (0x1204)
        """
        QMessageBox.information(self, "Draw Declined", 
                               "Your opponent declined the draw offer.")
    
    def on_resign(self):
        """
        Handle resign button
        Sends MSG_C2S_RESIGN (0x0021)
        """
        reply = QMessageBox.question(self, "Resign",
                                    "Are you sure you want to resign?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.network.resign(self.game_id)
            self.is_resigned = True
    
    def confirm_quit(self):
        """Confirm quit to lobby"""
        reply = QMessageBox.question(self, "Quit Game",
                                    "Are you sure you want to quit? The game will continue.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.quit_game.emit()
