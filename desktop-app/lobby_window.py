"""
Lobby Window - PyQt6
Main lobby after login with matchmaking options
Replaces React HomePage component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QListWidget, QMessageBox,
                            QComboBox, QListWidgetItem, QScrollArea, QTableWidget,
                            QTableWidgetItem, QHeaderView, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from network_client import MessageTypeS2C
from datetime import datetime


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
        self.game_history = []  # Store game history
        # Stats from server
        self.stats = {
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'total_games': 0
        }
        self.init_ui()
        self.setup_network_handlers()
        # Request game history on startup
        QTimer.singleShot(500, self.on_refresh_stats)
    
    def init_ui(self):
        """Initialize lobby UI"""
        self.setWindowTitle("Chess Lobby")
        self.setFixedSize(1280, 800)  # Increased height from 720 to 800
        
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
        
        # Left side - Matchmaking (30%)
        matchmaking_panel = self.create_matchmaking_panel()
        content_layout.addWidget(matchmaking_panel, 30)
        
        # Middle - Online Users (30%)
        online_users_panel = self.create_online_users_panel()
        content_layout.addWidget(online_users_panel, 30)
        
        # Right side - User stats (40%)
        stats_panel = self.create_stats_panel()
        content_layout.addWidget(stats_panel, 40)
        
        # Add content layout with stretch to fill remaining space
        main_layout.addLayout(content_layout, 1)
        
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
        title = QLabel("Chess Lobby")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        layout.addStretch()
        
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
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        
        # User info section
        user_info_frame = QFrame()
        user_info_frame.setStyleSheet("background-color: #e3f2fd; border-radius: 6px; padding: 10px;")
        user_info_layout = QVBoxLayout(user_info_frame)
        user_info_layout.setSpacing(5)
        
        username_label = QLabel(f"{self.user_data.get('username', 'Player')}")
        username_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        username_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        username_label.setStyleSheet("color: #1976d2;")
        user_info_layout.addWidget(username_label)
        
        rating_label = QLabel(f"Rating: {self.user_data.get('rating', 1500)}")
        rating_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        rating_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rating_label.setStyleSheet("color: #ff9800;")
        user_info_layout.addWidget(rating_label)
        
        layout.addWidget(user_info_frame)
        
        # Title
        title = QLabel("Find a Game")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Play Online section
        online_frame = QFrame()
        online_frame.setStyleSheet("background-color: #e8f5e9; border-radius: 6px; padding: 12px;")
        online_layout = QVBoxLayout(online_frame)
        online_layout.setSpacing(8)
        
        online_title = QLabel("Play Online")
        online_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        online_layout.addWidget(online_title)
        
        # Find Match button
        self.find_match_button = QPushButton("Find Match")
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
        self.cancel_button = QPushButton("Cancel Search")
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
        
        ai_title = QLabel("Play vs AI")
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
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ccc;
                background-color: white;
                selection-background-color: #4CAF50;
                selection-color: white;
                outline: none;
            }
        """)
        # Connect signal to ensure popup closes after selection
        self.difficulty_combo.activated.connect(lambda: self.difficulty_combo.hidePopup())
        difficulty_layout.addWidget(self.difficulty_combo)
        ai_layout.addLayout(difficulty_layout)
        
        # Play AI button
        self.play_ai_button = QPushButton("Start AI Game")
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
        
        return panel
    
    def create_online_users_panel(self):
        """Create online users list panel with challenge buttons"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        
        # Title
        title = QLabel("Online Players")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Online count
        self.online_count_label = QLabel("0 online")
        self.online_count_label.setStyleSheet("color: #4caf50; font-weight: bold; font-size: 12px;")
        self.online_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.online_count_label)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
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
        layout.addWidget(self.online_users_list, 1)  # Stretch to fill space
        
        # Challenge button
        self.challenge_button = QPushButton("Challenge Selected Player")
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
        
        # Load initial online users from server
        self.refresh_online_users()
        
        return panel
    
    def refresh_online_users(self):
        """Request online users from server"""
        print("🔄 Requesting online users from server...")
        self.network.get_online_users()
    
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
                item_text = f"{username} (Rating: {rating})"
                available_count += 1
            elif status == 'in_game':
                item_text = f"{username} (Rating: {rating}) - In Game"
            else:
                item_text = f"{username} (Rating: {rating})"
            
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
        opponent_user_id = user_data['user_id']
        opponent_rating = user_data.get('rating', '?')
        
        # Send challenge request to server
        self.network.challenge_player(opponent_user_id, opponent_username)
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Challenge Sent")
        msg_box.setText(f"Challenge sent to {opponent_username} (Rating: {opponent_rating})!\n\nWaiting for response...")
        msg_box.setStyleSheet("""
            QLabel { min-width: 350px; padding: 15px; font-size: 12px; }
            QPushButton { min-width: 80px; min-height: 30px; }
        """)
        msg_box.exec()
        
        # Disable button while waiting
        self.challenge_button.setEnabled(False)
        self.challenge_button.setText("⏳ Challenge Sent...")

    
    def on_refresh_online_users(self):
        """Refresh online users list"""
        print("🔄 Refreshing online users...")
        self.refresh_online_users()
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Refreshed")
        msg_box.setText("Requesting online users list...")
        msg_box.setStyleSheet("""
            QLabel { min-width: 250px; padding: 15px; font-size: 12px; }
            QPushButton { min-width: 80px; min-height: 30px; }
        """)
        msg_box.exec()
    
    def create_stats_panel(self):
        """Create game history panel"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        
        # Title
        title = QLabel("Game History")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Quick stats summary - Grid 2x2
        stats_summary = QFrame()
        stats_summary.setStyleSheet("background-color: #f5f5f5; border-radius: 4px; padding: 10px;")
        stats_layout = QGridLayout(stats_summary)
        stats_layout.setSpacing(10)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create stats labels that can be updated
        self.wins_label = QLabel("Wins: 0")
        self.wins_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.wins_label.setStyleSheet("color: #4caf50; padding: 8px; background-color: white; border-radius: 4px;")
        self.wins_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.wins_label, 0, 0)  # Row 0, Col 0
        
        self.losses_label = QLabel("Losses: 0")
        self.losses_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.losses_label.setStyleSheet("color: #f44336; padding: 8px; background-color: white; border-radius: 4px;")
        self.losses_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.losses_label, 0, 1)  # Row 0, Col 1
        
        self.draws_label = QLabel("Draws: 0")
        self.draws_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.draws_label.setStyleSheet("color: #ff9800; padding: 8px; background-color: white; border-radius: 4px;")
        self.draws_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.draws_label, 1, 0)  # Row 1, Col 0
        
        self.winrate_label = QLabel("Win Rate: 0%")
        self.winrate_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.winrate_label.setStyleSheet("color: #2196f3; padding: 8px; background-color: white; border-radius: 4px;")
        self.winrate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(self.winrate_label, 1, 1)  # Row 1, Col 1
        
        layout.addWidget(stats_summary)
        
        # Game history table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Opponent", "Result", "Time"])
        self.history_table.horizontalHeader().setVisible(True)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #2196f3;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.history_table, 1)  # Stretch to fill space
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
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
        elif message_id == MessageTypeS2C.HISTORY_RESPONSE:
            self.handle_history_response(data)
        elif message_id == MessageTypeS2C.ONLINE_USERS_LIST:
            self.handle_online_users_list(data)
        elif message_id == MessageTypeS2C.CHALLENGE_RECEIVED:
            self.handle_challenge_received(data)
        elif message_id == MessageTypeS2C.CHALLENGE_ACCEPTED:
            self.handle_challenge_accepted(data)
        elif message_id == MessageTypeS2C.CHALLENGE_DECLINED:
            self.handle_challenge_declined(data)

    
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
        
        self.match_status_label.setText(f"Match found vs {opponent} ({opponent_rating})!")
        
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
        Request updated stats and game history
        Sends MSG_C2S_GET_STATS (0x0030) and MSG_C2S_GET_HISTORY (0x0031)
        """
        self.network.get_stats()
        self.network.get_history()
    
    def handle_stats_response(self, data: dict):
        """
        Handle stats response
        Receives MSG_S2C_STATS_RESPONSE (0x1300)
        """
        if 'error' in data:
            print(f"❌ Stats error: {data['error']}")
            return
        
        # Update stats from server
        self.stats['wins'] = data.get('wins', 0)
        self.stats['losses'] = data.get('losses', 0)
        self.stats['draws'] = data.get('draws', 0)
        self.stats['total_games'] = data.get('total_games', 0)
        
        print(f"📊 Stats: W:{self.stats['wins']} L:{self.stats['losses']} D:{self.stats['draws']}")
        
        # Update UI
        self.update_stats_display()
    
    def update_stats_display(self):
        """Update the stats labels with current data"""
        wins = self.stats['wins']
        losses = self.stats['losses']
        draws = self.stats['draws']
        total = self.stats['total_games']
        
        # Update labels
        self.wins_label.setText(f"Wins: {wins}")
        self.losses_label.setText(f"Losses: {losses}")
        self.draws_label.setText(f"Draws: {draws}")
        
        # Calculate and update win rate
        win_rate = (wins / total * 100) if total > 0 else 0
        self.winrate_label.setText(f"Win Rate: {win_rate:.1f}%")
        
        print(f"📊 Stats displayed: W:{wins} L:{losses} D:{draws} Total:{total}")
    
    def handle_history_response(self, data: dict):
        """
        Handle game history response
        Receives MSG_S2C_HISTORY_RESPONSE (0x1301)
        """
        if 'error' in data:
            print(f"❌ History error: {data['error']}")
            return
        
        games = data.get('games', [])
        self.game_history = games
        print(f"📜 Received {len(games)} game history entries")
        
        # Debug: print first game if exists
        if games:
            print(f"📜 First game sample: {games[0]}")
        
        # Update history table
        self.update_history_table()
    
    def update_history_table(self):
        """Update the history table with game data"""
        self.history_table.setRowCount(0)
        
        print(f"📊 Updating history table with {len(self.game_history)} games")
        
        for game in self.game_history:
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            
            # Get opponent name from server response
            opponent = game.get('opponent', 'Unknown')
            
            # Opponent name
            opponent_item = QTableWidgetItem(opponent)
            opponent_item.setFont(QFont("Arial", 10))
            self.history_table.setItem(row, 0, opponent_item)
            
            # Result - use user_result from server (from user's perspective)
            user_result = game.get('user_result', 'unknown')
            
            if user_result == 'win':
                result_text = "Win"
                result_color = QColor(76, 175, 80)  # Green
            elif user_result == 'loss':
                result_text = "Loss"
                result_color = QColor(244, 67, 54)  # Red
            elif user_result == 'draw':
                result_text = "Draw"
                result_color = QColor(255, 152, 0)  # Orange
            else:
                result_text = "Unfinished"
                result_color = QColor(158, 158, 158)  # Gray
            
            result_item = QTableWidgetItem(result_text)
            result_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            result_item.setForeground(result_color)
            self.history_table.setItem(row, 1, result_item)
            
            # Time - use 'date' field from server
            date_str = game.get('date', 'N/A')
            
            time_item = QTableWidgetItem(date_str)
            time_item.setFont(QFont("Arial", 9))
            time_item.setForeground(QColor(117, 117, 117))
            self.history_table.setItem(row, 2, time_item)
        
        # Adjust row heights
        for i in range(self.history_table.rowCount()):
            self.history_table.setRowHeight(i, 35)
        
        print(f"✅ History table updated with {self.history_table.rowCount()} rows")
    
    def handle_online_users_list(self, data: dict):
        """
        Handle online users list response
        Receives MSG_S2C_ONLINE_USERS_LIST (0x1004)
        """
        if data.get('success'):
            users = data.get('users', [])
            print(f"📝 Received {len(users)} online users")
            self.update_online_users(users)
    
    def handle_challenge_received(self, data: dict):
        """
        Handle incoming challenge from another player
        Receives MSG_S2C_CHALLENGE_RECEIVED (0x1205)
        """
        challenger_username = data.get('challenger_username', 'Unknown')
        challenger_rating = data.get('challenger_rating', '?')
        challenger_id = data.get('challenger_id')
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚔️ Challenge Received!")
        msg_box.setText(f"{challenger_username} (Rating: {challenger_rating}) wants to challenge you!")
        msg_box.setInformativeText("Do you accept?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        result = msg_box.exec()
        
        # Send accept/decline response to server
        if result == QMessageBox.StandardButton.Yes:
            self.network.accept_challenge(challenger_id)
        else:
            self.network.decline_challenge(challenger_id)
    
    def handle_challenge_accepted(self, data: dict):
        """
        Handle challenge acceptance
        Receives MSG_S2C_CHALLENGE_ACCEPTED (0x1206)
        """
        opponent_username = data.get('opponent_username', 'Unknown')
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Challenge Accepted")
        msg_box.setText(f"{opponent_username} accepted your challenge!")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
        
        # Reset challenge button
        self.challenge_button.setEnabled(True)
        self.challenge_button.setText("Challenge Selected Player")
    
    def handle_challenge_declined(self, data: dict):
        """
        Handle challenge declined
        Receives MSG_S2C_CHALLENGE_DECLINED (0x1207)
        """
        opponent_username = data.get('opponent_username', 'Unknown')
        reason = data.get('reason', 'Challenge was declined')
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Challenge Declined")
        msg_box.setText(f"{opponent_username}: {reason}")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.exec()
        
        # Reset challenge button
        self.challenge_button.setEnabled(True)
        self.challenge_button.setText("Challenge Selected Player")
