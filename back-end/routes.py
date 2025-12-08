"""
Routes
Định nghĩa các API endpoints
"""
from aiohttp import web
from controllers.auth_controller import register, login, get_profile
from controllers.user_controller import get_user, get_users


async def register_handler(request):
    """Handler cho API đăng ký"""
    result = await register(request)
    return web.json_response(result)


async def login_handler(request):
    """Handler cho API đăng nhập"""
    result = await login(request)
    return web.json_response(result)


async def get_profile_handler(request):
    """Handler cho API lấy profile"""
    result = await get_profile(request)
    return web.json_response(result)


async def get_user_handler(request):
    """Handler cho API lấy user"""
    result = await get_user(request)
    return web.json_response(result)


async def get_users_handler(request):
    """Handler cho API lấy danh sách users"""
    result = await get_users(request)
    return web.json_response(result)


def setup_routes(app):
    """
    Thiết lập các routes cho app
    
    Auth routes:
        POST /api/auth/register - Đăng ký
        POST /api/auth/login - Đăng nhập
        GET /api/auth/profile - Lấy profile
    
    User routes:
        GET /api/users - Lấy danh sách users
        GET /api/user - Lấy thông tin user
    """
    # Auth routes
    app.router.add_post('/api/auth/register', register_handler)
    app.router.add_post('/api/auth/login', login_handler)
    app.router.add_get('/api/auth/profile', get_profile_handler)
    
    # User routes
    app.router.add_get('/api/users', get_users_handler)
    app.router.add_get('/api/user', get_user_handler)
    
    print("Routes setup completed")
    print("Available endpoints:")
    print("  POST /api/auth/register")
    print("  POST /api/auth/login")
    print("  GET /api/auth/profile")
    print("  GET /api/users")
    print("  GET /api/user")
