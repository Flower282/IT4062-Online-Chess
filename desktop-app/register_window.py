"""
Register Window - PyQt6
Replaces React Register.jsx component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from network_client import MessageTypeS2C
from ui_utils import ResponsiveUI


class RegisterWindow(QWidget):
    """
    Register window - Maps from React Register.jsx
    
    State management:
    - React useState -> Qt widget values and member variables
    - React useEffect -> Qt signals/slots
    - React onChange -> Built-in Qt signals (textChanged, etc.)
    """
    
    # Signals
    register_success = pyqtSignal()
    switch_to_login = pyqtSignal()
    
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.init_ui()
        self.setup_network_handlers()
    
    def init_ui(self):
        """Initialize UI - equivalent to React render()"""
        self.setWindowTitle("Chess Game - Register")
        self.setMinimumSize(400, 600)
        
        # Main layout with center alignment
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(20)
        
        # Header
        header = QLabel("Chess Game")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        subtitle = QLabel("Create your account")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        main_layout.addWidget(subtitle)
        
        # Form container
        form_frame = QFrame()
        form_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)
        
        # Username field
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Choose a username")
        self.username_input.setMinimumHeight(35)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #21ba45;
            }
        """)
        form_layout.addWidget(self.username_input)
        
        # Email field
        email_label = QLabel("Email:")
        email_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(35)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #21ba45;
            }
        """)
        form_layout.addWidget(self.email_input)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Choose a password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(35)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #21ba45;
            }
        """)
        form_layout.addWidget(self.password_input)
        
        # Confirm password field
        confirm_label = QLabel("Confirm Password:")
        confirm_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(confirm_label)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setMinimumHeight(35)
        self.confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #21ba45;
            }
        """)
        form_layout.addWidget(self.confirm_input)
        
        # Error message label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("""
            QLabel {
                color: #db2828;
                background-color: #fff6f6;
                border: 1px solid #db2828;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)
        
        # Success message label
        self.success_label = QLabel()
        self.success_label.setStyleSheet("""
            QLabel {
                color: #21ba45;
                background-color: #fcfff5;
                border: 1px solid #21ba45;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        self.success_label.setWordWrap(True)
        self.success_label.hide()
        form_layout.addWidget(self.success_label)
        
        # Register button - sends MSG_C2S_REGISTER (0x0001)
        self.register_button = QPushButton("Register")
        self.register_button.setMinimumHeight(40)
        self.register_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #21ba45;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #16ab39;
            }
            QPushButton:pressed {
                background-color: #198f35;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.register_button.clicked.connect(self.handle_register)
        form_layout.addWidget(self.register_button)
        
        # Press Enter to register
        self.confirm_input.returnPressed.connect(self.handle_register)
        
        main_layout.addWidget(form_frame)
        
        # Login link
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        login_label = QLabel("Already have an account?")
        login_label.setStyleSheet("color: #666;")
        login_layout.addWidget(login_label)
        
        self.login_link = QPushButton("Login")
        self.login_link.setFlat(True)
        self.login_link.setStyleSheet("""
            QPushButton {
                color: #2185d0;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1678c2;
            }
        """)
        self.login_link.clicked.connect(self.switch_to_login.emit)
        login_layout.addWidget(self.login_link)
        
        main_layout.addLayout(login_layout)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        self.setStyleSheet("QWidget { background-color: #f5f5f5; }")
    
    def setup_network_handlers(self):
        """Setup network message handlers"""
        self.network.message_received.connect(self.on_message_received)
    
    def on_message_received(self, message_id: int, data: dict):
        """Handle incoming messages"""
        if message_id == MessageTypeS2C.REGISTER_RESULT:
            self.handle_register_result(data)
    
    def handle_register(self):
        """
        Handle register button click
        Sends MSG_C2S_REGISTER (0x0001)
        """
        # Get input values
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        # Validation
        if not username or not email or not password or not confirm:
            self.show_error("Please fill in all fields")
            return
        
        if len(username) < 3:
            self.show_error("Username must be at least 3 characters")
            return
        
        if len(password) < 6:
            self.show_error("Password must be at least 6 characters")
            return
        
        if password != confirm:
            self.show_error("Passwords do not match")
            return
        
        if '@' not in email or '.' not in email:
            self.show_error("Please enter a valid email address")
            return
        
        # Clear messages
        self.error_label.hide()
        self.success_label.hide()
        
        # Disable button
        self.register_button.setEnabled(False)
        self.register_button.setText("Registering...")
        
        # Send TCP message 0x0001 (REGISTER)
        success = self.network.register(username, password, email)
        
        if not success:
            self.register_button.setEnabled(True)
            self.register_button.setText("Register")
            self.show_error("Failed to send registration request")
    
    def handle_register_result(self, data: dict):
        """
        Handle registration result
        Receives MSG_S2C_REGISTER_RESULT (0x1001)
        """
        # Re-enable button
        self.register_button.setEnabled(True)
        self.register_button.setText("Register")
        
        success = data.get('success', False)
        
        if success:
            # Registration successful
            message = data.get('message', 'Account created successfully!')
            self.show_success(message)
            
            # Clear form
            self.username_input.clear()
            self.email_input.clear()
            self.password_input.clear()
            self.confirm_input.clear()
            
            # Emit success signal (will switch to login after delay)
            self.register_success.emit()
        else:
            # Registration failed
            error_msg = data.get('error', 'Registration failed')
            self.show_error(error_msg)
    
    def show_error(self, message: str):
        """Display error message"""
        self.success_label.hide()
        self.error_label.setText(message)
        self.error_label.show()
    
    def show_success(self, message: str):
        """Display success message"""
        self.error_label.hide()
        self.success_label.setText(message)
        self.success_label.show()
    
    def clear_form(self):
        """Clear form inputs"""
        self.username_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.error_label.hide()
        self.success_label.hide()
        self.register_button.setEnabled(True)
        self.register_button.setText("Register")
