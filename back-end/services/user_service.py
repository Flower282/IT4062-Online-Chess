"""
User Service
Xử lý business logic liên quan đến User
"""
import bcrypt
from database import get_db_connection
from models.user import User
from bson import ObjectId


def hash_password(password):
    """Mã hóa mật khẩu bằng bcrypt với salt"""
    # Tạo salt và hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password, hashed_password):
    """Xác thực mật khẩu với hash đã lưu"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_user(fullname, username, password):
    """
    Tạo user mới
    
    Args:
        fullname (str): Họ và tên
        username (str): Tên đăng nhập
        password (str): Mật khẩu
        
    Returns:
        dict: {'success': bool, 'message': str, 'user_id': str}
    """
    try:
        db = get_db_connection()
        users_collection = db[User.get_collection_name()]
        
        # Kiểm tra username đã tồn tại chưa
        if users_collection.find_one({'username': username}):
            return {'success': False, 'message': 'Tên đăng nhập đã tồn tại'}
        
        # Hash password và lưu user với elo mặc định
        hashed_password = hash_password(password)
        user = User(fullname=fullname, username=username, password=hashed_password, elo=1200)
        
        result = users_collection.insert_one(user.to_dict(include_password=True))
        
        return {
            'success': True,
            'message': 'Đăng ký thành công',
            'user_id': str(result.inserted_id)
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}


def verify_user(username, password):
    """
    Xác thực đăng nhập
    
    Args:
        username (str): Tên đăng nhập
        password (str): Mật khẩu
        
    Returns:
        dict: {'success': bool, 'message': str, 'user': dict}
    """
    try:
        db = get_db_connection()
        users_collection = db[User.get_collection_name()]
        
        # Tìm user theo username
        user_doc = users_collection.find_one({'username': username})
        
        # Xác thực mật khẩu bằng bcrypt
        if user_doc and verify_password(password, user_doc['password']):
            user = User(
                _id=user_doc['_id'],
                fullname=user_doc['fullname'],
                username=user_doc['username'],
                password='',
                elo=user_doc.get('elo', 1200)
            )
            
            return {
                'success': True,
                'message': 'Đăng nhập thành công',
                'user': user.to_dict()
            }
        else:
            return {'success': False, 'message': 'Tên đăng nhập hoặc mật khẩu không đúng'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}


def get_user_by_username(username):
    """
    Lấy thông tin user theo username
    
    Args:
        username (str): Tên đăng nhập
        
    Returns:
        dict: Thông tin user hoặc None
    """
    try:
        db = get_db_connection()
        users_collection = db[User.get_collection_name()]
        
        user_doc = users_collection.find_one({'username': username})
        
        if user_doc:
            user = User(
                _id=user_doc['_id'],
                fullname=user_doc['fullname'],
                username=user_doc['username'],
                password='',
                elo=user_doc.get('elo', 1200)
            )
            return user.to_dict()
        
        return None
    
    except Exception as e:
        return None


def get_all_users():
    """
    Lấy danh sách tất cả users
    
    Returns:
        list: Danh sách users
    """
    try:
        db = get_db_connection()
        users_collection = db[User.get_collection_name()]
        
        users_docs = users_collection.find({}, {'password': 0})  # Không lấy password
        
        users = []
        for doc in users_docs:
            user = User(
                _id=doc['_id'],
                fullname=doc['fullname'],
                username=doc['username'],
                password='',
                elo=doc.get('elo', 1200)
            )
            users.append(user.to_dict())
        
        return users
    
    except Exception as e:

        return []
