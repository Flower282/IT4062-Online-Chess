"""
JWT Utilities
Các hàm tiện ích để tạo và xác thực JWT tokens
"""
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps
from aiohttp import web

# Secret key để mã hóa JWT (nên lưu trong biến môi trường)
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 ngày


def create_access_token(user_data):
    """
    Tạo JWT access token
    
    Args:
        user_data (dict): Thông tin user cần encode vào token
            {
                'id': int,
                'username': str,
                'fullname': str,
                'elo': int
            }
    
    Returns:
        str: JWT token string
    """
    try:
        # Tạo payload
        payload = {
            'user_id': user_data.get('id'),
            'username': user_data.get('username'),
            'fullname': user_data.get('fullname'),
            'elo': user_data.get('elo', 1200),
            'exp': datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            'iat': datetime.utcnow()
        }
        
        # Encode token
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
        
    except Exception as e:
        print(f"Error creating token: {e}")
        return None


def decode_access_token(token):
    """
    Giải mã và xác thực JWT token
    
    Args:
        token (str): JWT token string
    
    Returns:
        dict: Payload của token nếu hợp lệ, None nếu không hợp lệ
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None


def get_token_from_request(request):
    """
    Lấy token từ header Authorization của request
    
    Args:
        request: aiohttp request object
    
    Returns:
        str: Token string hoặc None
    """
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Bỏ "Bearer " prefix
    
    return None


def token_required(handler):
    """
    Decorator để bảo vệ các route cần xác thực
    
    Usage:
        @token_required
        async def protected_handler(request):
            # request['user'] sẽ chứa thông tin user từ token
            user = request['user']
            ...
    """
    @wraps(handler)
    async def wrapper(request):
        # Lấy token từ header
        token = get_token_from_request(request)
        
        if not token:
            return web.json_response(
                {
                    'success': False,
                    'message': 'Token không tồn tại. Vui lòng đăng nhập lại.'
                },
                status=401
            )
        
        # Xác thực token
        payload = decode_access_token(token)
        
        if not payload:
            return web.json_response(
                {
                    'success': False,
                    'message': 'Token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.'
                },
                status=401
            )
        
        # Thêm thông tin user vào request để handler có thể sử dụng
        request['user'] = payload
        
        # Gọi handler gốc
        return await handler(request)
    
    return wrapper
