"""
Main Application - PyQt6 Chess Desktop App
Entry point that manages all windows and application state
"""

import sys
from PyQt6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from network_client import NetworkClient
from login_window import LoginWindow
from register_window import RegisterWindow
from lobby_window import LobbyWindow
from game_window import GameWindow


class ChessApplication(QStackedWidget):
    """
    Main application class using QStackedWidget
    Manages navigation between different windows
    
    React Router equivalent:
    - QStackedWidget replaces BrowserRouter + Routes
    - setCurrentWidget() replaces history.push()
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize network client
        self.network = NetworkClient(host='localhost', port=8765)
        
        # User session data
        self.user_data = None
        self.current_game = None
        
        # Initialize UI
        self.init_ui()
        
        # Connect to server
        self.connect_to_server()
    
    def init_ui(self):
        """Initialize application UI"""
        self.setWindowTitle("Chess Desktop App")
        
        # Set fixed size 1280x720
        self.setFixedSize(1280, 720)
        
        # Create windows
        self.login_window = LoginWindow(self.network)
        self.register_window = RegisterWindow(self.network)
        self.lobby_window = None  # Created after login
        self.game_window = None   # Created when game starts
        
        # Add initial windows to stack
        self.addWidget(self.login_window)
        self.addWidget(self.register_window)
        
        # Setup window signals
        self.setup_signals()
        
        # Start with login window
        self.setCurrentWidget(self.login_window)
        
        # Center window on screen
        self.center_on_screen()
    
    def center_on_screen(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def setup_signals(self):
        """Setup signal connections between windows"""
        # Login window signals
        self.login_window.login_success.connect(self.on_login_success)
        self.login_window.switch_to_register.connect(self.show_register)
        
        # Register window signals
        self.register_window.register_success.connect(self.on_register_success)
        self.register_window.switch_to_login.connect(self.show_login)
        
        # Network signals
        self.network.connected.connect(self.on_network_connected)
        self.network.disconnected.connect(self.on_network_disconnected)
        self.network.error_occurred.connect(self.on_network_error)
    
    def connect_to_server(self):
        """Connect to TCP server"""
        print("Connecting to server...")
        success = self.network.connect_to_server()
        
        if not success:
            QMessageBox.critical(self, "Connection Error",
                               "Failed to connect to server.\n"
                               "Make sure the server is running on localhost:8765")
    
    def on_network_connected(self):
        """Handle successful connection"""
        print("✓ Connected to server")
    
    def on_network_disconnected(self):
        """Handle disconnection"""
        print("✗ Disconnected from server")
        
        # Show error and return to login
        QMessageBox.warning(self, "Disconnected",
                          "Connection to server lost.\n"
                          "Please reconnect.")
        
        # Return to login screen
        self.show_login()
    
    def on_network_error(self, error_msg: str):
        """Handle network errors"""
        print(f"Network error: {error_msg}")
        # Errors are shown in individual windows as needed
    
    def show_login(self):
        """Show login window"""
        self.login_window.clear_form()
        self.setCurrentWidget(self.login_window)
        self.setWindowTitle("Chess - Login")
    
    def show_register(self):
        """Show register window"""
        self.register_window.clear_form()
        self.setCurrentWidget(self.register_window)
        self.setWindowTitle("Chess - Register")
    
    def on_login_success(self, user_data: dict):
        """
        Handle successful login
        Transition: Login -> Lobby
        """
        print(f"Login successful: {user_data}")
        self.user_data = user_data
        
        # Create lobby window
        self.show_lobby()
    
    def on_register_success(self):
        """
        Handle successful registration
        Transition: Register -> Login (after delay)
        """
        print("Registration successful")
        
        # Show message and redirect to login after delay
        QTimer.singleShot(2000, self.show_login)
    
    def show_lobby(self):
        """Show lobby window"""
        # Create lobby window if not exists
        if self.lobby_window is None:
            self.lobby_window = LobbyWindow(self.network, self.user_data)
            self.lobby_window.logout_requested.connect(self.on_logout)
            self.lobby_window.start_game.connect(self.on_game_start)
            self.addWidget(self.lobby_window)
        
        self.setCurrentWidget(self.lobby_window)
        self.setWindowTitle(f"Chess Lobby - {self.user_data.get('username')}")
    
    def on_game_start(self, game_data: dict):
        """
        Handle game start
        Transition: Lobby -> Game
        """
        print(f"Starting game: {game_data}")
        self.current_game = game_data
        
        # Create game window
        self.game_window = GameWindow(self.network, game_data, self.user_data)
        self.game_window.quit_game.connect(self.on_game_quit)
        
        # Remove old game window if exists
        for i in range(self.count()):
            widget = self.widget(i)
            if isinstance(widget, GameWindow) and widget != self.game_window:
                self.removeWidget(widget)
                widget.deleteLater()
        
        self.addWidget(self.game_window)
        self.setCurrentWidget(self.game_window)
        self.setWindowTitle(f"Chess Game - {self.user_data.get('username')}")
    
    def on_game_quit(self):
        """
        Handle game quit
        Transition: Game -> Lobby
        """
        print("Quitting game")
        self.current_game = None
        
        # Return to lobby
        if self.lobby_window:
            self.setCurrentWidget(self.lobby_window)
            self.setWindowTitle(f"Chess Lobby - {self.user_data.get('username')}")
    
    def on_logout(self):
        """
        Handle logout
        Transition: Lobby -> Login
        """
        print("Logging out")
        
        # Clear user data
        self.user_data = None
        self.current_game = None
        
        # Remove lobby window
        if self.lobby_window:
            self.removeWidget(self.lobby_window)
            self.lobby_window.deleteLater()
            self.lobby_window = None
        
        # Return to login
        self.show_login()
    
    def closeEvent(self, event):
        """Handle application close"""
        # Confirm quit
        reply = QMessageBox.question(self, "Quit",
                                    "Are you sure you want to quit?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Disconnect from server
            if self.network.connected_flag:
                self.network.disconnect_from_server()
            
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Chess Desktop App")
    app.setOrganizationName("IT4062")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = ChessApplication()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
