"""
Stats Handler
Xử lý thống kê và lịch sử game
"""

from services.game_service import (
    get_user_game_history, get_user_stats, get_game, get_game_pgn
)


class StatsHandler:
    """Handler cho stats và history"""
    
    def __init__(self, network_manager):
        """
        Args:
            network_manager: Instance của NetworkManager
        """
        self.network = network_manager
        self.MessageTypeS2C = None  # Will be set by server
    
    def handle_get_stats(self, client_fd: int, data: dict):
        """
        0x0030 - GET_STATS: Hệ thống Xếp hạng: Yêu cầu xem thống kê (ELO, W/L/D)
        """
        user_id = data.get('user_id', None)
        
        # If no user_id provided, use current session user
        if not user_id:
            session = self.network.client_sessions.get(client_fd, {})
            user_id = session.get('user_id')
        
        print(f"📊 Stats request from fd={client_fd} for user {user_id}")
        
        # Get stats from database
        stats = get_user_stats(user_id)
        
        if stats:
            # Send stats response (0x1300 - STATS_RESPONSE)
            self.network.send_to_client(client_fd, self.MessageTypeS2C.STATS_RESPONSE, stats)
        else:
            self.network.send_to_client(client_fd, self.MessageTypeS2C.STATS_RESPONSE, {
                'error': 'User not found'
            })
    
    def handle_get_history(self, client_fd: int, data: dict):
        """
        0x0031 - GET_HISTORY: Hệ thống Lịch sử: Yêu cầu xem lịch sử các ván đấu
        """
        print(f"📜 History request from fd={client_fd}")
        
        # Get user session
        session = self.network.client_sessions.get(client_fd, {})
        user_id = session.get('user_id')
        
        if user_id:
            # Get game history from database
            history = get_user_game_history(user_id, limit=20)
            
            # Send history response (0x1301 - HISTORY_RESPONSE)
            self.network.send_to_client(client_fd, self.MessageTypeS2C.HISTORY_RESPONSE, {
                'games': history
            })
        else:
            self.network.send_to_client(client_fd, self.MessageTypeS2C.HISTORY_RESPONSE, {
                'games': [],
                'error': 'Not authenticated'
            })
