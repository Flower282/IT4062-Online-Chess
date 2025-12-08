"""
Auth Controller
Xử lý đăng ký, đăng nhập, đăng xuất
"""
from services.user_service import create_user, verify_user, get_user_by_username


async def register(request):
    """
    API đăng ký user mới
    
    Request body:
        {
            "fullname": "string",
            "username": "string", 
            "password": "string"
        }
    
    Response:
        {
            "success": bool,
            "message": "string",
            "user_id": int (optional)
        }
    """
    try:
        data = await request.json()
        fullname = data.get('fullname', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not fullname or not username or not password:
            return {
                'success': False,
                'message': 'Vui lòng điền đầy đủ thông tin'
            }
        
        if len(username) < 3:
            return {
                'success': False,
                'message': 'Tên đăng nhập phải có ít nhất 3 ký tự'
            }
        
        if len(password) < 6:
            return {
                'success': False,
                'message': 'Mật khẩu phải có ít nhất 6 ký tự'
            }
        
        # Tạo user
        result = create_user(fullname, username, password)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }


async def login(request):
    """
    API đăng nhập
    
    Request body:
        {
            "username": "string",
            "password": "string"
        }
    
    Response:
        {
            "success": bool,
            "message": "string",
            "user": {
                "id": int,
                "fullname": "string",
                "username": "string"
            } (optional)
        }
    """
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not password:
            return {
                'success': False,
                'message': 'Vui lòng điền đầy đủ thông tin'
            }
        
        # Xác thực user
        result = verify_user(username, password)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }


async def get_profile(request):
    """
    API lấy thông tin profile user
    
    Query params:
        username: string
    
    Response:
        {
            "success": bool,
            "user": {
                "id": int,
                "fullname": "string",
                "username": "string",
                "created_at": "string"
            } (optional)
        }
    """
    try:
        username = request.query.get('username', '').strip()
        
        if not username:
            return {
                'success': False,
                'message': 'Thiếu username'
            }
        
        user = get_user_by_username(username)
        
        if user:
            return {
                'success': True,
                'user': user
            }
        else:
            return {
                'success': False,
                'message': 'Không tìm thấy user'
            }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }


async def register(request):
    """
    API đăng ký user mới
    
    Request body:
        {
            "fullname": "string",
            "username": "string", 
            "password": "string"
        }
    
    Response:
        {
            "success": bool,
            "message": "string",
            "user_id": int (optional)
        }
    """
    try:
        data = await request.json()
        fullname = data.get('fullname', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not fullname or not username or not password:
            return {
                'success': False,
                'message': 'Vui lòng điền đầy đủ thông tin'
            }
        
        if len(username) < 3:
            return {
                'success': False,
                'message': 'Tên đăng nhập phải có ít nhất 3 ký tự'
            }
        
        if len(password) < 6:
            return {
                'success': False,
                'message': 'Mật khẩu phải có ít nhất 6 ký tự'
            }
        
        # Tạo user
        result = create_user(fullname, username, password)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }


async def login(request):
    """
    API đăng nhập
    
    Request body:
        {
            "username": "string",
            "password": "string"
        }
    
    Response:
        {
            "success": bool,
            "message": "string",
            "user": {
                "id": int,
                "fullname": "string",
                "username": "string"
            } (optional)
        }
    """
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username or not password:
            return {
                'success': False,
                'message': 'Vui lòng điền đầy đủ thông tin'
            }
        
        # Xác thực user
        result = verify_user(username, password)
        return result
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }


async def get_profile(request):
    """
    API lấy thông tin profile user
    
    Query params:
        username: string
    
    Response:
        {
            "success": bool,
            "user": {
                "id": int,
                "fullname": "string",
                "username": "string",
                "created_at": "string"
            } (optional)
        }
    """
    try:
        username = request.query.get('username', '').strip()
        
        if not username:
            return {
                'success': False,
                'message': 'Thiếu username'
            }
        
        user = get_user_by_username(username)
        
        if user:
            return {
                'success': True,
                'user': user
            }
        else:
            return {
                'success': False,
                'message': 'Không tìm thấy user'
            }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }
