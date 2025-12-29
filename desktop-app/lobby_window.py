"""
Lobby Window - PyQt6
Main lobby after login with matchmaking options
Replaces React HomePage component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QListWidget, QMessageBox,
                            QComboBox, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from network_client import MessageTypeS2C


class LobbyWindow(QWidget):
    """
    Lobby window with matchmaking options
    
    React state mapping:
    - useState(currentUser) -> self.user_data
    - useState(onlineUsers) -> self.online_users_list
    - useState(waitingForResponse) -> self.is_waiting
    
    React events:
    - socket.emit('find_match') -> MSG_C2S_FIND_MATCH (0x0010)
    - socket.on('match_found') -> MSG_S2C_MATCH_FOUND (0x1100)
    """
    
    # Signals
    logout_requested = pyqtSignal()
    start_game = pyqtSignal(dict)  # game_data
    
    def __init__(self, network_client, user_data, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.user_data = user_data
        self.is_waiting = False
        self.init_ui()
        self.setup_network_handlers()
    
    def init_ui(self):
        """Initialize lobby UI"""
        self.setWindowTitle("Chess Lobby")
        self.setMinimumSize(800, 600)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        
        # Header with user info
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area with matchmaking and stats
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left side - Matchmaking
        matchmaking_panel = self.create_matchmaking_panel()
        content_layout.addWidget(matchmaking_panel, 2)
        
        # Right side - User stats and info
        stats_panel = self.create_stats_panel()
        content_layout.addWidget(stats_panel, 1)
        
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
        self.setStyleSheet("QWidget { background-color: #f5f5f5; }")
    
    def create_header(self):
        """Create header with user info"""
        header = QFrame()
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header.setStyleSheet("""
            QFrame {
                background-color: #2196f3;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Title
        title = QLabel("♔ Chess Lobby ♔")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # User info
        username_label = QLabel(f"Welcome, {self.user_data.get('username', 'Player')}!")
        username_label.setFont(QFont("Arial", 14))
        username_label.setStyleSheet("color: white;")
        layout.addWidget(username_label)
        
        rating_label = QLabel(f"Rating: {self.user_data.get('rating', 1500)}")
        rating_label.setFont(QFont("Arial", 12))
        rating_label.setStyleSheet("color: #e3f2fd;")
        layout.addWidget(rating_label)
        
        # Logout button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.logout_button.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.logout_button)
        
        return header
    
    def create_matchmaking_panel(self):
        """Create matchmaking panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Find a Game")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Play Online section
        online_frame = QFrame()
        online_frame.setStyleSheet("background-color: #f9f9f9; border-radius: 4px; padding: 15px;")
        online_layout = QVBoxLayout(online_frame)
        
        online_title = QLabel("Play Online")
        online_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        online_layout.addWidget(online_title)
        
        online_desc = QLabel("Find a random opponent")
        online_desc.setStyleSheet("color: #666;")
        online_layout.addWidget(online_desc)
        
        # Find Match button - sends MSG_C2S_FIND_MATCH (0x0010)
        self.find_match_button = QPushButton("🎯 Find Match")
        self.find_match_button.setMinimumHeight(50)
        self.find_match_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.find_match_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.find_match_button.clicked.connect(self.on_find_match)
        online_layout.addWidget(self.find_match_button)
        
        # Cancel button (hidden by default)
        self.cancel_button = QPushButton("❌ Cancel Search")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setFont(QFont("Arial", 12))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel_match)
        self.cancel_button.hide()
        online_layout.addWidget(self.cancel_button)
        
        # Status label
        self.match_status_label = QLabel("")
        self.match_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.match_status_label.setStyleSheet("color: #2196f3; font-weight: bold;")
        self.match_status_label.hide()
        online_layout.addWidget(self.match_status_label)
        
        layout.addWidget(online_frame)
        
        # Play AI section
        ai_frame = QFrame()
        ai_frame.setStyleSheet("background-color: #f9f9f9; border-radius: 4px; padding: 15px;")
        ai_layout = QVBoxLayout(ai_frame)
        
        ai_title = QLabel("Play vs AI")
        ai_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        ai_layout.addWidget(ai_title)
        
        ai_desc = QLabel("Practice against computer")
        ai_desc.setStyleSheet("color: #666;")
        ai_layout.addWidget(ai_desc)
        
        # Difficulty selection
        difficulty_layout = QHBoxLayout()
        difficulty_label = QLabel("Difficulty:")
        difficulty_layout.addWidget(difficulty_label)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Easy", "Medium", "Hard"])
        self.difficulty_combo.setCurrentText("Medium")
        self.difficulty_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        difficulty_layout.addWidget(self.difficulty_combo)
        ai_layout.addLayout(difficulty_layout)
        
        # Play AI button - sends MSG_C2S_FIND_AI_MATCH (0x0012)
        self.play_ai_button = QPushButton("🤖 Play vs AI")
        self.play_ai_button.setMinimumHeight(50)
        self.play_ai_button.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.play_ai_button.setStyleSheet("""
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
        self.play_ai_button.clicked.connect(self.on_play_ai)
        ai_layout.addWidget(self.play_ai_button)
        
        layout.addWidget(ai_frame)
        
        layout.addStretch()
        
        return panel
    
    def create_stats_panel(self):
        """Create user stats panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Your Statistics")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Stats
        stats_data = [
            ("Rating", self.user_data.get('rating', 1500)),
            ("Wins", self.user_data.get('wins', 0)),
            ("Losses", self.user_data.get('losses', 0)),
            ("Draws", self.user_data.get('draws', 0))
        ]
        
        for label, value in stats_data:
            stat_frame = QFrame()
            stat_frame.setStyleSheet("background-color: #f9f9f9; border-radius: 4px; padding: 10px;")
            stat_layout = QHBoxLayout(stat_frame)
            
            name_label = QLabel(label)
            name_label.setFont(QFont("Arial", 12))
            stat_layout.addWidget(name_label)
            
            stat_layout.addStretch()
            
            value_label = QLabel(str(value))
            value_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2196f3;")
            stat_layout.addWidget(value_label)
            
            layout.addWidget(stat_frame)
        
        layout.addStretch()
        
        # Refresh stats button
        refresh_button = QPushButton("🔄 Refresh Stats")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        refresh_button.clicked.connect(self.on_refresh_stats)
        layout.addWidget(refresh_button)
        
        return panel
    
    def setup_network_handlers(self):
        """Setup network message handlers"""
        self.network.message_received.connect(self.on_message_received)
    
    def on_message_received(self, message_id: int, data: dict):
        """Handle incoming messages"""
        if message_id == MessageTypeS2C.MATCH_FOUND:
            self.handle_match_found(data)
        elif message_id == MessageTypeS2C.GAME_START:
            self.handle_game_start(data)
        elif message_id == MessageTypeS2C.STATS_RESPONSE:
            self.handle_stats_response(data)
    
    def on_find_match(self):
        """
        Handle find match button
        Sends MSG_C2S_FIND_MATCH (0x0010)
        """
        self.is_waiting = True
        
        # Update UI
        self.find_match_button.setEnabled(False)
        self.play_ai_button.setEnabled(False)
        self.cancel_button.show()
        self.match_status_label.setText("🔍 Searching for opponent...")
        self.match_status_label.show()
        
        # Send request
        self.network.find_match()
    
    def on_cancel_match(self):
        """
        Handle cancel match button
        Sends MSG_C2S_CANCEL_FIND_MATCH (0x0011)
        """
        self.is_waiting = False
        
        # Update UI
        self.find_match_button.setEnabled(True)
        self.play_ai_button.setEnabled(True)
        self.cancel_button.hide()
        self.match_status_label.hide()
        
        # Send cancel request
        self.network.cancel_find_match()
    
    def handle_match_found(self, data: dict):
        """
        Handle match found notification
        Receives MSG_S2C_MATCH_FOUND (0x1100)
        """
        self.is_waiting = False
        
        opponent = data.get('opponent_username', 'Unknown')
        opponent_rating = data.get('opponent_rating', '?')
        
        self.match_status_label.setText(f"✓ Match found vs {opponent} ({opponent_rating})!")
        
        # Match found, wait for GAME_START message
    
    def handle_game_start(self, data: dict):
        """
        Handle game start
        Receives MSG_S2C_GAME_START (0x1101)
        """
        # Reset UI
        self.find_match_button.setEnabled(True)
        self.play_ai_button.setEnabled(True)
        self.cancel_button.hide()
        self.match_status_label.hide()
        
        # Start game with data
        self.start_game.emit(data)
    
    def on_play_ai(self):
        """
        Handle play AI button
        Sends MSG_C2S_FIND_AI_MATCH (0x0012)
        """
        difficulty = self.difficulty_combo.currentText().lower()
        
        # Send AI match request
        self.network.find_ai_match(difficulty)
        
        # Show loading
        self.play_ai_button.setEnabled(False)
        self.play_ai_button.setText("Starting game...")
    
    def on_refresh_stats(self):
        """
        Request updated stats
        Sends MSG_C2S_GET_STATS (0x0030)
        """
        self.network.get_stats()
    
    def handle_stats_response(self, data: dict):
        """
        Handle stats response
        Receives MSG_S2C_STATS_RESPONSE (0x1300)
        """
        # Update user data and UI
        self.user_data.update(data)
        
        # Refresh stats display
        # TODO: Update stat labels dynamically
        
        QMessageBox.information(self, "Stats Updated", "Your statistics have been refreshed!")
