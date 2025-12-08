"""
User Controller
Xử lý các thao tác liên quan đến user
"""
from services.user_service import get_user_by_username, get_all_users


async def get_user(request):
    """
    API lấy thông tin user theo username
    
    Query params:
        username: string
    
    Response:
        {
            "success": bool,
            "user": dict (optional),
            "message": "string" (optional)
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


async def get_users(request):
    """
    API lấy danh sách tất cả users
    
    Response:
        {
            "success": bool,
            "users": list,
            "count": int
        }
    """
    try:
        users = get_all_users()
        
        return {
            'success': True,
            'users': users,
            'count': len(users)
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'Lỗi server: {str(e)}',
            'users': [],
            'count': 0
        }
