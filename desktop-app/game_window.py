"""
Game Window - PyQt6
Main game interface with chess board and controls
Replaces React ChessBoard.jsx component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFrame, QMessageBox,
                            QDialog, QDialogButtonBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from chess_board_widget import ChessBoardWidget
from network_client import MessageTypeS2C, MessageTypeC2S
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
        self.is_resigned = False
        self.opponent_resigned = False
        
        # Timer variables
        self.move_time_limit = 60  # 60 seconds per move
        self.current_time_left = self.move_time_limit
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)  # Update every second
        
        # Store game_id for requests
        self.game_id = game_data.get('game_id', '')
        
        # Determine player color
        self.my_color = game_data.get('color', 'white')
        
        # Get opponent name - handle both AI and human opponents
        opponent_username = game_data.get('opponent_username', 'Unknown')
        opponent_id = game_data.get('opponent_id', 0)
        
        # Check if playing against AI
        if opponent_id == -1 or 'AI Bot' in opponent_username:
            # AI opponent - name already formatted as "AI Bot (Difficulty)"
            self.opponent_name = opponent_username
        else:
            # Human opponent
            self.opponent_name = opponent_username
        
        self.init_ui()
        self.setup_network_handlers()
    
    def init_ui(self):
        """Initialize game UI"""
        self.setWindowTitle("Chess Game")
        self.setFixedSize(1280, 853)
        
        # Main horizontal layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Left side - Move history and info (25%)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 25)
        
        # Center - Chess board (50%)
        board_container = self.create_board_container()
        main_layout.addWidget(board_container, 50)
        
        # Right side - Controls (25%)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 25)
        
        self.setLayout(main_layout)
        self.setStyleSheet("""
            QWidget { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e3f2fd, stop:1 #f5f5f5);
            }
        """)
    
    def create_left_panel(self):
        """Create left panel with move history"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Move History")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1976d2; padding: 5px;")
        layout.addWidget(title)
        
        # Opponent info
        opponent_frame = QFrame()
        opponent_frame.setStyleSheet("""
            background-color: #424242; 
            border-radius: 8px; 
            padding: 12px;
            border: 2px solid #616161;
        """)
        opponent_layout = QVBoxLayout(opponent_frame)
        opponent_layout.setSpacing(5)
        
        opponent_icon = QLabel("Opponent")
        opponent_icon.setFont(QFont("Arial", 9))
        opponent_icon.setStyleSheet("color: #bdbdbd;")
        opponent_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opponent_layout.addWidget(opponent_icon)
        
        self.opponent_label = QLabel(self.opponent_name)
        self.opponent_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.opponent_label.setStyleSheet("color: white;")
        self.opponent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opponent_layout.addWidget(self.opponent_label)
        
        opponent_color = 'Black' if self.my_color == 'white' else 'White'
        self.opponent_color_label = QLabel(opponent_color)
        self.opponent_color_label.setFont(QFont("Arial", 10))
        self.opponent_color_label.setStyleSheet("color: #90caf9;")
        self.opponent_color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opponent_layout.addWidget(self.opponent_color_label)
        
        layout.addWidget(opponent_frame)
        
        # Move history text area
        self.move_history = QTextEdit()
        self.move_history.setReadOnly(True)
        self.move_history.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.move_history, 1)
        
        # Player info (you)
        player_frame = QFrame()
        player_frame.setStyleSheet("""
            background-color: #1976d2; 
            border-radius: 8px; 
            padding: 12px;
            border: 2px solid #1565c0;
        """)
        player_layout = QVBoxLayout(player_frame)
        player_layout.setSpacing(5)
        
        player_icon = QLabel("You")
        player_icon.setFont(QFont("Arial", 9))
        player_icon.setStyleSheet("color: #bbdefb;")
        player_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(player_icon)
        
        self.player_label = QLabel(self.user_data.get('username', 'You'))
        self.player_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.player_label.setStyleSheet("color: white;")
        self.player_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(self.player_label)
        
        player_color = f"{self.my_color.capitalize()}"
        self.player_color_label = QLabel(player_color)
        self.player_color_label.setFont(QFont("Arial", 10))
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
                border: 3px solid #424242;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        # Game status label
        initial_status = "Your turn" if self.my_color == 'white' else "Opponent's turn"
        self.status_label = QLabel(initial_status)
        self.status_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            color: #1976d2; 
            padding: 12px; 
            background-color: #e3f2fd;
            border-radius: 8px;
        """)
        # Timer label
        self.timer_label = QLabel("Time: 60s")
        self.timer_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("""
            color: #d32f2f; 
            padding: 12px; 
            background-color: #ffebee;
            border-radius: 8px;
            border: 1px solid #ffcdd2;
        """)
        layout.addWidget(self.timer_label)
        
        layout.addWidget(self.status_label)
        
        # Chess board widget
        self.chess_board = ChessBoardWidget(orientation=self.my_color, piece_style='neo')
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
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Game Controls")
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #1976d2; padding: 5px;")
        layout.addWidget(title)
        
        # Piece style selector
        style_frame = QFrame()
        style_frame.setStyleSheet("""
            background-color: #f5f5f5; 
            border: 1px solid #e0e0e0;
            border-radius: 8px; 
            padding: 10px;
        """)
        style_layout = QVBoxLayout(style_frame)
        style_layout.setSpacing(8)
        
        style_label = QLabel("Kiểu quân cờ:")
        style_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        style_label.setStyleSheet("color: #424242;")
        style_layout.addWidget(style_label)
        
        self.piece_style_combo = QComboBox()
        self.piece_style_combo.addItems([
            'neo', 'classic', 'light', 'tournament', 
            'newspaper', 'ocean', '8bit'
        ])
        self.piece_style_combo.setCurrentText('neo')
        self.piece_style_combo.setFont(QFont("Arial", 10))
        self.piece_style_combo.setMaxVisibleItems(7)  # Limit visible items to prevent large dropdown
        self.piece_style_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.piece_style_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #2196f3;
                border-radius: 6px;
                padding: 8px;
                color: #424242;
                min-height: 25px;
            }
            QComboBox:hover {
                border-color: #1976d2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #424242;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #2196f3;
                border-radius: 6px;
                selection-background-color: #2196f3;
                selection-color: white;
                padding: 5px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2196f3;
                color: white;
            }
        """)
        # Use activated signal instead of currentTextChanged - only fires on user interaction
        self.piece_style_combo.activated.connect(self.on_piece_style_changed)
        style_layout.addWidget(self.piece_style_combo)
        
        layout.addWidget(style_frame)
        
        # Offer Draw button - sends MSG_C2S_OFFER_DRAW (0x0022)
        self.draw_button = QPushButton("Offer Draw")
        self.draw_button.setMinimumHeight(45)
        self.draw_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.draw_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)
        self.draw_button.clicked.connect(self.on_offer_draw)
        layout.addWidget(self.draw_button)
        
        # Resign button - sends MSG_C2S_RESIGN (0x0021)
        self.resign_button = QPushButton("Resign")
        self.resign_button.setMinimumHeight(45)
        self.resign_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.resign_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.resign_button.clicked.connect(self.on_resign)
        layout.addWidget(self.resign_button)
        
        # Game info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            background-color: #f5f5f5; 
            border: 1px solid #e0e0e0;
            border-radius: 8px; 
            padding: 12px;
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        
        info_title = QLabel("Game Info")
        info_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_title.setStyleSheet("color: #424242;")
        info_layout.addWidget(info_title)
        
        game_id_label = QLabel(f"ID: {self.game_data.get('game_id', 'N/A')}")
        game_id_label.setFont(QFont("Courier New", 9))
        game_id_label.setStyleSheet("color: #757575;")
        info_layout.addWidget(game_id_label)
        
        layout.addWidget(info_frame)
        
        layout.addStretch()
        
        # Quit button
        self.quit_button = QPushButton("Back to Lobby")
        self.quit_button.setMinimumHeight(45)
        self.quit_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #424242;
            }
        """)
        self.quit_button.clicked.connect(self.confirm_quit)
        layout.addWidget(self.quit_button)
        
        return panel
    
    def on_piece_style_changed(self, index):
        """Handle piece style change"""
        # Get the text from the selected index
        style = self.piece_style_combo.itemText(index)
        
        # Close popup immediately
        self.piece_style_combo.hidePopup()
        
        # Use QTimer to update board after popup closes
        # This ensures the popup closes smoothly before the potentially heavy update
        QTimer.singleShot(0, lambda: self._update_piece_style(style))
    
    def _update_piece_style(self, style):
        """Internal method to update piece style"""
        if self.chess_board:
            self.chess_board.set_piece_style(style)
    
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
    
    def on_move_made(self, from_square: str, to_square: str, promotion: str):
        """
        Handle move made on board
        Sends MSG_C2S_MAKE_MOVE (0x0020)
        """
        # Send move to server with game_id and promotion piece if any
        self.network.make_move(self.game_id, from_square, to_square, promotion if promotion else None)
        
        # Update status
        self.status_label.setText("Waiting for server...")
        
        # Reset timer
        self.reset_timer()
    
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
            self.status_label.setStyleSheet("""
                color: white; 
                padding: 12px; 
                font-weight: bold;
                background-color: #4caf50;
                border-radius: 8px;
            """)
        else:
            self.status_label.setText("Opponent's turn")
            self.status_label.setStyleSheet("""
                color: white; 
                padding: 12px; 
                font-weight: bold;
                background-color: #ff9800;
                border-radius: 8px;
            """)
        
        # Check for check
        if data.get('is_check'):
            self.status_label.setText(self.status_label.text() + " CHECK!")
            self.status_label.setStyleSheet("""
                color: white; 
                padding: 12px; 
                font-weight: bold;
                background-color: #f44336;
                border-radius: 8px;
            """)
        
        
        # Note: Game over is handled separately by GAME_OVER message (0x1202)
        # not from GAME_STATE_UPDATE to ensure we receive outcome/message info
        
        # Reset timer on turn change
        self.reset_timer()
    
    def update_timer(self):
        """Update countdown timer"""
        if self.current_time_left > 0:
            self.current_time_left -= 1
            self.timer_label.setText(f"Time: {self.current_time_left}s")
            
            # Visual warning when low time
            if self.current_time_left <= 10:
                self.timer_label.setStyleSheet("""
                    color: white; 
                    background-color: #d32f2f;
                    padding: 12px; 
                    border-radius: 8px;
                    font-weight: bold;
                """)
            else:
                self.timer_label.setStyleSheet("""
                    color: #d32f2f; 
                    padding: 12px; 
                    background-color: #ffebee;
                    border-radius: 8px;
                    border: 1px solid #ffcdd2;
                """)
    
    def reset_timer(self):
        """Reset move timer"""
        self.current_time_left = self.move_time_limit
        self.timer_label.setText(f"Time: {self.current_time_left}s")
        self.timer_label.setStyleSheet("""
            color: #d32f2f; 
            padding: 12px; 
            background-color: #ffebee;
            border-radius: 8px;
            border: 1px solid #ffcdd2;
        """)
    
    def closeEvent(self, event):
        """Handle window close"""
        self.timer.stop()
        super().closeEvent(event)
    
    def handle_invalid_move(self, data: dict):
        """
        Handle invalid move error
        Receives MSG_S2C_INVALID_MOVE (0x1201)
        """
        error = data.get('error', 'Invalid move')
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Invalid Move")
        msg_box.setText(error)
        msg_box.setStyleSheet("""
            QLabel { min-width: 300px; padding: 15px; font-size: 12px; }
            QPushButton { min-width: 80px; min-height: 30px; }
        """)
        msg_box.exec()
        
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
        # Sử dụng outcome từ backend (you_win, you_loss, draw)
        outcome = data.get('outcome', '')
        message_text = data.get('message', '')
        result = data.get('result', 'unknown')
        
        # Xác định title và message dựa trên outcome
        if outcome == 'you_win':
            title = "Victory"
            message = message_text or "You won! 🎉"
        elif outcome == 'you_loss':
            title = "Defeat"
            message = message_text or "You lost."
        elif outcome == 'draw':
            title = "Draw"
            message = message_text or "Game ended in a draw."
        else:
            # Fallback to old logic nếu không có outcome
            winner = data.get('winner', None)
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
        
        # Show message box with larger size
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Set larger font and size
        font = QFont()
        font.setPointSize(12)
        msg_box.setFont(font)
        msg_box.setStyleSheet("""
            QMessageBox {
                min-width: 400px;
                min-height: 200px;
            }
            QLabel {
                min-width: 350px;
                min-height: 80px;
                padding: 20px;
                font-size: 14px;
            }
            QPushButton {
                min-width: 100px;
                min-height: 35px;
                font-size: 12px;
                padding: 5px 15px;
            }
        """)
        msg_box.exec()
        
        # Return to lobby
        self.quit_game.emit()
    
    def on_offer_draw(self):
        """
        Handle offer draw button
        Sends MSG_C2S_OFFER_DRAW (0x0022)
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Offer Draw")
        msg_box.setText("Do you want to offer a draw to your opponent?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QMessageBox {
                min-width: 400px;
            }
            QLabel {
                min-width: 350px;
                padding: 15px;
                font-size: 13px;
            }
            QPushButton {
                min-width: 90px;
                min-height: 32px;
                font-size: 12px;
            }
        """)
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.network.offer_draw(self.game_id)
            info_box = QMessageBox(self)
            info_box.setWindowTitle("Draw Offer")
            info_box.setText("Draw offer sent to opponent.")
            info_box.setStyleSheet("""
                QLabel { min-width: 300px; padding: 15px; font-size: 12px; }
                QPushButton { min-width: 80px; min-height: 30px; }
            """)
            info_box.exec()
    
    def handle_draw_offer_received(self, data: dict):
        """
        Handle draw offer from opponent
        Receives MSG_S2C_DRAW_OFFER_RECEIVED (0x1203)
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Draw Offer")
        msg_box.setText("Your opponent offers a draw. Do you accept?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QMessageBox { min-width: 400px; }
            QLabel { min-width: 350px; padding: 15px; font-size: 13px; }
            QPushButton { min-width: 90px; min-height: 32px; font-size: 12px; }
        """)
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            # Send MSG_C2S_ACCEPT_DRAW (0x0023) with game_id
            self.network.send_message(MessageTypeC2S.ACCEPT_DRAW, {
                'game_id': self.game_id
            })
        else:
            # Send MSG_C2S_DECLINE_DRAW (0x0024) with game_id
            self.network.send_message(MessageTypeC2S.DECLINE_DRAW, {
                'game_id': self.game_id
            })
    
    def handle_draw_offer_declined(self, data: dict):
        """
        Handle draw offer declined
        Receives MSG_S2C_DRAW_OFFER_DECLINED (0x1204)
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Draw Declined")
        msg_box.setText("Your opponent declined the draw offer.")
        msg_box.setStyleSheet("""
            QLabel { min-width: 300px; padding: 15px; font-size: 12px; }
            QPushButton { min-width: 80px; min-height: 30px; }
        """)
        msg_box.exec()
    
    def on_resign(self):
        """
        Handle resign button
        Sends MSG_C2S_RESIGN (0x0021)
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Resign")
        msg_box.setText("Are you sure you want to resign?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QMessageBox { min-width: 400px; }
            QLabel { min-width: 300px; padding: 15px; font-size: 13px; }
            QPushButton { min-width: 90px; min-height: 32px; font-size: 12px; }
        """)
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.network.resign(self.game_id)
            self.is_resigned = True
    
    def confirm_quit(self):
        """Confirm quit to lobby"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Quit Game")
        msg_box.setText("Are you sure you want to quit? The game will continue.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet("""
            QMessageBox { min-width: 400px; }
            QLabel { min-width: 350px; padding: 15px; font-size: 13px; }
            QPushButton { min-width: 90px; min-height: 32px; font-size: 12px; }
        """)
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self.quit_game.emit()
