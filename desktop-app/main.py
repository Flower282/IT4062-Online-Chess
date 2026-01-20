"""
Main Application - PyQt6 Chess Desktop App
Entry point that manages all windows and application state
DPI-aware and cross-platform compatible
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from network_client import NetworkClient
from login_window import LoginWindow
from register_window import RegisterWindow
from lobby_window import LobbyWindow
from game_window import GameWindow
from ui_utils import ResponsiveUI, CenteredMessageBox
from config import (SERVER_HOST, SERVER_PORT, APP_TITLE, 
                   MIN_APP_WIDTH, MIN_APP_HEIGHT, 
                   PREFERRED_APP_WIDTH, PREFERRED_APP_HEIGHT,
                   FONT_FAMILY_FALLBACK, ENABLE_HIGH_DPI)


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
        self.network = NetworkClient(host=SERVER_HOST, port=SERVER_PORT)
        
        # User session data
        self.user_data = None
        self.current_game = None
        
        # Initialize UI
        self.init_ui()
        
        # Note: connect_to_server() is called AFTER window is shown (see main())
    
    def init_ui(self):
        """Initialize application UI - Fixed size 960x600"""
        self.setWindowTitle(APP_TITLE)
        
        # Fixed window size - 960x600 pixels
        app_width = 960
        app_height = 600
        
        # Set fixed window size (not resizable)
        self.setFixedSize(app_width, app_height)
        
        # Store dimensions for child windows
        self.app_width = app_width
        self.app_height = app_height
        
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
    
    def center_on_screen(self):
        """Center the window on screen"""
        # Process all pending events to ensure window is fully rendered
        QApplication.processEvents()
        
        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate center position
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        
        # Move window to center
        self.move(x, y)
    
    def center_dialog(self, dialog):
        """Center a dialog on this window"""
        # Ensure dialog has been sized
        dialog.adjustSize()
        
        # Get parent window geometry
        parent_x = self.x()
        parent_y = self.y()
        parent_width = self.width()
        parent_height = self.height()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog.width()) // 2
        y = parent_y + (parent_height - dialog.height()) // 2
        
        # Move dialog to center
        dialog.move(x, y)
    
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
        """Connect to TCP server - MUST be called after window is shown"""
        # Ensure window is visible before showing dialogs
        if not self.isVisible():
            print("Warning: connect_to_server() called before window is visible!")
            return
        
        print("Connecting to server...")
        success = self.network.connect_to_server()
        
        if not success:
            # Process any pending events to ensure window geometry is updated
            QApplication.processEvents()
            
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Connection Error")
            msg_box.setText("Failed to connect to server.\nMake sure the server is running on localhost:8765")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet(ResponsiveUI.get_messagebox_stylesheet())
            msg_box.setWindowModality(Qt.WindowModality.WindowModal)
            
            # Use CenteredMessageBox for Linux-compatible centering
            CenteredMessageBox.show_and_exec(msg_box, self)
    
    def on_network_connected(self):
        """Handle successful connection"""
        print("✓ Connected to server")
    
    def on_network_disconnected(self):
        """Handle disconnection"""
        print("✗ Disconnected from server")
        
        # Show error and return to login
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Disconnected")
        msg_box.setText("Connection to server lost.\nPlease reconnect.")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet(ResponsiveUI.get_messagebox_stylesheet())
        msg_box.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Use CenteredMessageBox for Linux-compatible centering
        CenteredMessageBox.show_and_exec(msg_box, self)
        
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
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Quit")
        msg_box.setText("Are you sure you want to quit?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(ResponsiveUI.get_messagebox_stylesheet())
        msg_box.setWindowModality(Qt.WindowModality.WindowModal)
        
        # Use CenteredMessageBox for Linux-compatible centering
        reply = CenteredMessageBox.show_and_exec(msg_box, self)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Disconnect from server
            if self.network.is_connected():
                self.network.disconnect_from_server()
            
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point - DPI-aware configuration"""
    
    # Enable high DPI support BEFORE creating QApplication
    if ENABLE_HIGH_DPI:
        # Enable High DPI scaling (Qt 6 automatic)
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        
        # Set DPI awareness for better rendering on different displays
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Chess Desktop App")
    app.setOrganizationName("IT4062")
    
    # Set cross-platform font
    font = QFont()
    font.setFamilies(FONT_FAMILY_FALLBACK)
    app.setFont(font)
    
    # Set application style (Fusion is cross-platform consistent)
    app.setStyle('Fusion')
    
    # Get DPI info for debugging
    screen = app.primaryScreen()
    dpi = screen.logicalDotsPerInch()
    physical_dpi = screen.physicalDotsPerInch()
    print(f"🖥️  Display DPI: Logical={dpi:.1f}, Physical={physical_dpi:.1f}")
    print(f"📐 Screen: {screen.size().width()}x{screen.size().height()}")
    
    # Create and show main window
    window = ChessApplication()
    window.show()
    
    # Center window after it's fully rendered (using QTimer to ensure it's processed)
    QTimer.singleShot(0, window.center_on_screen)
    
    # Connect to server AFTER window is shown and centered
    # This ensures any error dialogs have a valid, visible parent window
    QTimer.singleShot(100, window.connect_to_server)
    
    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
