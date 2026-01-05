"""
Authentication Handler
Xử lý đăng ký và đăng nhập
"""

from services.user_service import create_user, verify_user


class AuthHandler:
    """Handler cho authentication (register, login)"""
    
    def __init__(self, network_manager):
        """
        Args:
            network_manager: Instance của NetworkManager
        """
        self.network = network_manager
        self.MessageTypeS2C = None  # Will be set by server
    
    def handle_register(self, client_fd: int, data: dict):
        """
        0x0001 - REGISTER: Quản lý người dùng: Yêu cầu đăng ký
        """
        username = data.get('username', '')
        password = data.get('password', '')
        email = data.get('email', '')
        fullname = data.get('fullname', username)
        
        print(f"📝 Register attempt: {username} ({email})")
        
        # Create user in database
        result = create_user(fullname=fullname, username=username, password=password)
        
        # Send register result (0x1001 - REGISTER_RESULT)
        self.network.send_to_client(client_fd, self.MessageTypeS2C.REGISTER_RESULT, {
            'success': result['success'],
            'message': result['message']
        })
    
    def handle_login(self, client_fd: int, data: dict):
        """
        0x0002 - LOGIN: Quản lý người dùng: Yêu cầu đăng nhập
        """
        username = data.get('email', '').split('@')[0] if '@' in data.get('email', '') else data.get('username', '')
        password = data.get('password', '')
        
        print(f"🔐 Login attempt: {username}")
        
        # Verify credentials from database
        result = verify_user(username=username, password=password)
        
        if result['success']:
            user = result['user']
            
            # Update session
            self.network.update_client_session(
                client_fd,
                authenticated=True,
                username=user['username'],
                user_id=user['_id'],
                fullname=user['fullname'],
                rating=user['elo']
            )
            
            # Send login result (0x1002 - LOGIN_RESULT)
            self.network.send_to_client(client_fd, self.MessageTypeS2C.LOGIN_RESULT, {
                'success': True,
                'user_id': user['_id'],
                'username': user['username'],
                'fullname': user['fullname'],
                'rating': user['elo'],
                'wins': 0,
                'losses': 0,
                'draws': 0
            })
        else:
            # Send login failure
            self.network.send_to_client(client_fd, self.MessageTypeS2C.LOGIN_RESULT, {
                'success': False,
                'message': result['message']
            })
    
    def handle_get_online_users(self, client_fd: int, data: dict):
        """
        0x0003 - GET_ONLINE_USERS: Lấy danh sách người chơi online
        """
        print(f"👥 Get online users request from fd={client_fd}")
        
        # Get current user info
        current_session = self.network.get_client_info(client_fd)
        current_username = current_session.get('username') if current_session else None
        
        # Build online users list
        online_users = []
        for fd, session in self.network.client_sessions.items():
            # Skip unauthenticated clients
            if not session.get('authenticated'):
                continue
            
            # Skip current user
            username = session.get('username')
            if username == current_username:
                continue
            
            # Check if user is in game
            game_id = session.get('game_id')
            status = 'in_game' if game_id else 'available'
            
            # Add to list
            online_users.append({
                'user_id': session.get('user_id'),
                'username': username,
                'fullname': session.get('fullname', username),
                'rating': session.get('rating', 1200),
                'status': status
            })
        
        # Send response (0x1004 - ONLINE_USERS_LIST)
        self.network.send_to_client(client_fd, self.MessageTypeS2C.ONLINE_USERS_LIST, {
            'success': True,
            'users': online_users
        })
        
        print(f"📝 Sent {len(online_users)} online users to fd={client_fd}")
