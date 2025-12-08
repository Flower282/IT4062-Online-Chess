"""
User Model
Định nghĩa schema và các thuộc tính của User
"""

class User:
    """
    Model User với các thuộc tính:
    - _id: ID của user (MongoDB ObjectId)
    - fullname: Họ và tên
    - username: Tên đăng nhập (unique)
    - password: Mật khẩu (đã mã hóa)
    - elo: Điểm Elo của người chơi (mặc định 1200)
    """
    
    def __init__(self, fullname, username, password, _id=None, elo=1200):
        self._id = _id
        self.fullname = fullname
        self.username = username
        self.password = password
        self.elo = elo
    
    def to_dict(self, include_password=False):
        """
        Chuyển đổi object thành dictionary
        
        Args:
            include_password (bool): Có bao gồm password hay không
        """
        data = {
            'fullname': self.fullname,
            'username': self.username,
            'elo': self.elo
        }
        
        if self._id:
            data['_id'] = str(self._id)
        
        if include_password:
            data['password'] = self.password
            
        return data
    
    @staticmethod
    def get_collection_name():
        """Trả về tên collection trong MongoDB"""
        return 'users'

