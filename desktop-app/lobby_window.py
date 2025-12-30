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
        self.setFixedSize(1280, 720)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with user info
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area with 3 columns: matchmaking, online users, stats
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left side - Matchmaking (35%)
        matchmaking_panel = self.create_matchmaking_panel()
        content_layout.addWidget(matchmaking_panel, 35)
        
        # Middle - Online Users (35%)
        online_users_panel = self.create_online_users_panel()
        content_layout.addWidget(online_users_panel, 35)
        
        # Right side - User stats (30%)
        stats_panel = self.create_stats_panel()
        content_layout.addWidget(stats_panel, 30)
        
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
        self.setStyleSheet("QWidget { background-color: #f5f5f5; }")
    
    def create_header(self):
        """Create header with user info"""
        header = QFrame()
        header.setFixedHeight(70)
        header.setFrameStyle(QFrame.Shape.StyledPanel)
        header.setStyleSheet("""
            QFrame {
                background-color: #2196f3;
                border-radius: 8px;
                padding: 10px 15px;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Title
        title = QLabel("♔ Chess Lobby ♔")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # User info
        username_label = QLabel(f"Welcome, {self.user_data.get('username', 'Player')}!")
        username_label.setFont(QFont("Arial", 13))
        username_label.setStyleSheet("color: white;")
        layout.addWidget(username_label)
        
        rating_label = QLabel(f"⭐ {self.user_data.get('rating', 1500)}")
        rating_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        rating_label.setStyleSheet("color: #ffd700;")
        layout.addWidget(rating_label)
        
        # Logout button
        self.logout_button = QPushButton("Logout")
        self.logout_button.setFixedSize(80, 35)
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
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
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("🎮 Find a Game")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Play Online section
        online_frame = QFrame()
        online_frame.setStyleSheet("background-color: #e8f5e9; border-radius: 6px; padding: 12px;")
        online_layout = QVBoxLayout(online_frame)
        online_layout.setSpacing(8)
        
        online_title = QLabel("⚔️ Play Online")
        online_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        online_layout.addWidget(online_title)
        
        # Find Match button
        self.find_match_button = QPushButton("🎯 Find Match")
        self.find_match_button.setMinimumHeight(45)
        self.find_match_button.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.find_match_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 6px;
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
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setFont(QFont("Arial", 11))
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
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
        self.match_status_label.setStyleSheet("color: #2196f3; font-weight: bold; font-size: 12px;")
        self.match_status_label.hide()
        online_layout.addWidget(self.match_status_label)
        
        layout.addWidget(online_frame)
        
        # Play AI section
        ai_frame = QFrame()
        ai_frame.setStyleSheet("background-color: #fff3e0; border-radius: 6px; padding: 12px;")
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setSpacing(8)
        
        ai_title = QLabel("🤖 Play vs AI")
        ai_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        ai_layout.addWidget(ai_title)
        
        # Difficulty selection
        difficulty_layout = QHBoxLayout()
        difficulty_label = QLabel("Difficulty:")
        difficulty_label.setStyleSheet("font-size: 11px;")
        difficulty_layout.addWidget(difficulty_label)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["Easy", "Medium", "Hard"])
        self.difficulty_combo.setCurrentText("Medium")
        self.difficulty_combo.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        difficulty_layout.addWidget(self.difficulty_combo)
        ai_layout.addLayout(difficulty_layout)
        
        # Play AI button
        self.play_ai_button = QPushButton("🤖 Start AI Game")
        self.play_ai_button.setMinimumHeight(45)
        self.play_ai_button.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.play_ai_button.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 6px;
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
    
    def create_online_users_panel(self):
        """Create online users list panel with challenge buttons"""
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
        layout.setSpacing(10)
        
        # Title with online count
        title_layout = QHBoxLayout()
        title = QLabel("👥 Online Players")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        self.online_count_label = QLabel("0 online")
        self.online_count_label.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 12px;")
        title_layout.addWidget(self.online_count_label)
        
        layout.addLayout(title_layout)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(30)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        refresh_btn.clicked.connect(self.on_refresh_online_users)
        layout.addWidget(refresh_btn)
        
        # Online users list
        self.online_users_list = QListWidget()
        self.online_users_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QListWidget::item:selected {
                background-color: #bbdefb;
                color: black;
            }
        """)
        layout.addWidget(self.online_users_list)
        
        # Challenge button
        self.challenge_button = QPushButton("⚔️ Challenge Selected Player")
        self.challenge_button.setMinimumHeight(40)
        self.challenge_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.challenge_button.setEnabled(False)
        self.challenge_button.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover:enabled {
                background-color: #7b1fa2;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #888;
            }
        """)
        self.challenge_button.clicked.connect(self.on_challenge_player)
        layout.addWidget(self.challenge_button)
        
        # Enable/disable challenge button based on selection
        self.online_users_list.itemSelectionChanged.connect(self.on_user_selection_changed)
        
        # Load initial online users
        self.load_demo_users()
        
        return panel
    
    def load_demo_users(self):
        """Load demo online users (placeholder until real data from server)"""
        demo_users = [
            {"username": "ChessMaster", "rating": 1650, "status": "available"},
            {"username": "KnightRider", "rating": 1520, "status": "in_game"},
            {"username": "QueenGambit", "rating": 1800, "status": "available"},
            {"username": "PawnStorm", "rating": 1420, "status": "available"},
            {"username": "RookieMoves", "rating": 1350, "status": "available"},
        ]
        
        self.update_online_users(demo_users)
    
    def update_online_users(self, users_list):
        """Update online users list"""
        self.online_users_list.clear()
        
        available_count = 0
        for user in users_list:
            # Skip self
            if user['username'] == self.user_data.get('username'):
                continue
            
            username = user['username']
            rating = user.get('rating', '?')
            status = user.get('status', 'available')
            
            # Create list item
            if status == 'available':
                item_text = f"🟢 {username} (⭐ {rating})"
                available_count += 1
            elif status == 'in_game':
                item_text = f"🔴 {username} (⭐ {rating}) - In Game"
            else:
                item_text = f"⚫ {username} (⭐ {rating})"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, user)  # Store user data
            self.online_users_list.addItem(item)
        
        # Update count
        total = self.online_users_list.count()
        self.online_count_label.setText(f"{total} online ({available_count} available)")
    
    def on_user_selection_changed(self):
        """Handle user selection change"""
        selected_items = self.online_users_list.selectedItems()
        if selected_items:
            user_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            # Only enable challenge if user is available
            is_available = user_data.get('status') == 'available'
            self.challenge_button.setEnabled(is_available)
        else:
            self.challenge_button.setEnabled(False)
    
    def on_challenge_player(self):
        """Send challenge to selected player"""
        selected_items = self.online_users_list.selectedItems()
        if not selected_items:
            return
        
        user_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        opponent_username = user_data['username']
        opponent_rating = user_data.get('rating', '?')
        
        # TODO: Send challenge request to server
        # self.network.send_challenge(opponent_user_id)
        
        QMessageBox.information(
            self, 
            "Challenge Sent", 
            f"Challenge sent to {opponent_username} (⭐ {opponent_rating})!\n\nWaiting for response..."
        )
        
        # Disable button while waiting
        self.challenge_button.setEnabled(False)
        self.challenge_button.setText("⏳ Challenge Sent...")
    
    def on_refresh_online_users(self):
        """Refresh online users list"""
        # TODO: Request online users from server
        # self.network.get_online_users()
        
        # For now, reload demo users
        self.load_demo_users()
        QMessageBox.information(self, "Refreshed", "Online users list refreshed!")
    
    def create_stats_panel(self):
        """Create user stats panel"""
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
        layout.setSpacing(12)
        
        # Title
        title = QLabel("📊 Your Stats")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Stats (rating removed - already shown in header)
        stats_data = [
            ("✅ Wins", self.user_data.get('wins', 0), "#4caf50"),
            ("❌ Losses", self.user_data.get('losses', 0), "#f44336"),
            ("🤝 Draws", self.user_data.get('draws', 0), "#ff9800")
        ]
        
        for label, value, color in stats_data:
            stat_frame = QFrame()
            stat_frame.setStyleSheet(f"background-color: #f9f9f9; border-left: 4px solid {color}; border-radius: 4px; padding: 10px;")
            stat_layout = QHBoxLayout(stat_frame)
            stat_layout.setContentsMargins(8, 5, 8, 5)
            
            name_label = QLabel(label)
            name_label.setFont(QFont("Arial", 11))
            stat_layout.addWidget(name_label)
            
            stat_layout.addStretch()
            
            value_label = QLabel(str(value))
            value_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            value_label.setStyleSheet(f"color: {color};")
            stat_layout.addWidget(value_label)
            
            layout.addWidget(stat_frame)
        
        # Total games
        total_games = self.user_data.get('wins', 0) + self.user_data.get('losses', 0) + self.user_data.get('draws', 0)
        win_rate = (self.user_data.get('wins', 0) / total_games * 100) if total_games > 0 else 0
        
        total_frame = QFrame()
        total_frame.setStyleSheet("background-color: #e8eaf6; border-radius: 4px; padding: 10px;")
        total_layout = QVBoxLayout(total_frame)
        total_layout.setSpacing(5)
        
        total_label = QLabel(f"Total Games: {total_games}")
        total_label.setFont(QFont("Arial", 11))
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_layout.addWidget(total_label)
        
        winrate_label = QLabel(f"Win Rate: {win_rate:.1f}%")
        winrate_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        winrate_label.setStyleSheet("color: #3f51b5;")
        winrate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_layout.addWidget(winrate_label)
        
        layout.addWidget(total_frame)
        
        layout.addStretch()
        
        # Refresh stats button
        refresh_button = QPushButton("🔄 Refresh Stats")
        refresh_button.setFixedHeight(35)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
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
