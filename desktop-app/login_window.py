"""
Login Window - PyQt6
Replaces React Login.jsx component
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QMessageBox, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from network_client import MessageTypeS2C


class LoginWindow(QWidget):
    """
    Login window - Maps from React Login.jsx
    
    React state mapping:
    - useState(username) -> self.username_input
    - useState(password) -> self.password_input
    - useState(error) -> QMessageBox for errors
    - useState(loading) -> self.login_button.setEnabled(False)
    
    React events mapping:
    - onClick={handleSubmit} -> self.login_button.clicked.connect(self.handle_login)
    - onChange={setUsername} -> Built-in QLineEdit signal
    """
    
    # Signal to switch to home page after successful login
    login_success = pyqtSignal(dict)  # Emits user data
    switch_to_register = pyqtSignal()
    
    def __init__(self, network_client, parent=None):
        super().__init__(parent)
        self.network = network_client
        self.init_ui()
        self.setup_network_handlers()
    
    def init_ui(self):
        """Initialize UI components - equivalent to React render()"""
        self.setWindowTitle("Chess Game - Login")
        self.setMinimumSize(400, 500)
        
        # Main layout - equivalent to React Container
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(20)
        
        # Header - equivalent to React Header component
        header = QLabel("♔ Chess Game ♔")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)
        
        subtitle = QLabel("Login to play")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        main_layout.addWidget(subtitle)
        
        # Form container - equivalent to React Segment
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
        
        # Username field - equivalent to React Form.Input
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(35)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #2185d0;
            }
        """)
        form_layout.addWidget(self.username_input)
        
        # Password field - equivalent to React Form.Input type="password"
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        form_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
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
                border: 2px solid #2185d0;
            }
        """)
        form_layout.addWidget(self.password_input)
        
        # Error message label (hidden by default)
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
        
        # Login button - equivalent to React Button onClick={handleSubmit}
        self.login_button = QPushButton("Login")
        self.login_button.setMinimumHeight(40)
        self.login_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2185d0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1678c2;
            }
            QPushButton:pressed {
                background-color: #1a69a4;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.login_button.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_button)
        
        # Press Enter to login
        self.password_input.returnPressed.connect(self.handle_login)
        
        main_layout.addWidget(form_frame)
        
        # Register link - equivalent to React Link
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        register_label = QLabel("Don't have an account?")
        register_label.setStyleSheet("color: #666;")
        register_layout.addWidget(register_label)
        
        self.register_link = QPushButton("Register")
        self.register_link.setFlat(True)
        self.register_link.setStyleSheet("""
            QPushButton {
                color: #2185d0;
                border: none;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #1678c2;
            }
        """)
        self.register_link.clicked.connect(self.switch_to_register.emit)
        register_layout.addWidget(self.register_link)
        
        main_layout.addLayout(register_layout)
        
        # Add stretch at bottom
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # Set window background
        self.setStyleSheet("QWidget { background-color: #f5f5f5; }")
    
    def setup_network_handlers(self):
        """Setup handlers for network responses"""
        # React equivalent: useEffect(() => { socket.on('login_result', ...) })
        self.network.message_received.connect(self.on_message_received)
    
    def on_message_received(self, message_id: int, data: dict):
        """
        Handle incoming messages from server
        React equivalent: socket.on() event handlers
        """
        if message_id == MessageTypeS2C.LOGIN_RESULT:
            self.handle_login_result(data)
    
    def handle_login(self):
        """
        Handle login button click
        React equivalent: handleSubmit function in Login.jsx
        
        Sends message: MSG_C2S_LOGIN (0x0002)
        """
        # Get input values
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Validation - React equivalent: if (!username || !password)
        if not username or not password:
            self.show_error("Please fill in all fields")
            return
        
        # Clear previous errors
        self.error_label.hide()
        
        # Disable button during request - React equivalent: setLoading(true)
        self.login_button.setEnabled(False)
        self.login_button.setText("Logging in...")
        
        # Send TCP message 0x0002 (LOGIN)
        success = self.network.login(username, password)
        
        if not success:
            self.login_button.setEnabled(True)
            self.login_button.setText("Login")
            self.show_error("Failed to send login request")
    
    def handle_login_result(self, data: dict):
        """
        Handle login result from server
        React equivalent: Response handler in loginUser API call
        
        Receives message: MSG_S2C_LOGIN_RESULT (0x1002)
        """
        # Re-enable button
        self.login_button.setEnabled(True)
        self.login_button.setText("Login")
        
        success = data.get('success', False)
        
        if success:
            # Login successful - React equivalent: history.push('/home')
            user_data = {
                'user_id': data.get('user_id'),
                'username': data.get('username'),
                'rating': data.get('rating', 1500),
                'wins': data.get('wins', 0),
                'losses': data.get('losses', 0),
                'draws': data.get('draws', 0)
            }
            
            print(f"✓ Login successful: {user_data['username']}")
            
            # Emit signal to switch to home page
            self.login_success.emit(user_data)
        else:
            # Login failed - React equivalent: setError(response.error)
            error_msg = data.get('error', 'Login failed')
            self.show_error(error_msg)
    
    def show_error(self, message: str):
        """
        Display error message
        React equivalent: setError(message) + Message component
        """
        self.error_label.setText(message)
        self.error_label.show()
    
    def clear_form(self):
        """Clear form inputs"""
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.hide()
        self.login_button.setEnabled(True)
        self.login_button.setText("Login")
