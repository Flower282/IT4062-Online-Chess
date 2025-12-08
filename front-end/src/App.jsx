import React, { useState, useEffect } from 'react';
import './css/App.css';
import { BrowserRouter as Router, Route, Redirect } from 'react-router-dom';
import { Header, Icon, Card, List, Segment, Grid, Button } from 'semantic-ui-react';
import { PrivateRoute, Login, Register, ChessBoard } from './routes/router';
import NewGameButtons from './components/NewGameButtons.jsx';
import Toast from './components/Toast.jsx';
import ChallengeModal from './components/ChallengeModal.jsx';
import { getCurrentUser, getAllUsers, getUser, logoutUser } from './api/user';
import { useHistory } from 'react-router-dom';
import socket from './SocketConfig';

// Component trang chủ sau khi đăng nhập
function HomePage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [toast, setToast] = useState(null);
  const [challengeModal, setChallengeModal] = useState({ open: false, senderInfo: null });
  const history = useHistory();

  useEffect(() => {
    // Lấy thông tin user hiện tại từ localStorage
    const user = getCurrentUser();
    console.log('Current user from localStorage:', user);
    
    // Nếu không có user trong localStorage, lấy từ username cũ
    if (!user) {
      const username = localStorage.getItem('username');
      if (username) {
        // Fetch thông tin đầy đủ từ API
        fetchUserInfo(username);
      }
    } else {
      setCurrentUser(user);
      
      // Emit user_login to server immediately after getting user info
      socket.emit('user_login', {
        username: user.username,
        fullname: user.fullname || user.username,
        elo: user.elo || 1200
      });
      
      console.log('Emitted user_login:', user.username);
    }

    // Listen for real-time online users updates from server
    socket.on('update_online_users', (data) => {
      console.log('Received update_online_users:', data);
      if (data.users) {
        setOnlineUsers(data.users);
      }
    });

    // Socket listeners for challenge feature
    socket.on('receive_challenge', (data) => {
      console.log('Received challenge:', data);
      setChallengeModal({
        open: true,
        senderInfo: data.senderInfo
      });
    });

    socket.on('challenge_sent', (data) => {
      console.log('Challenge sent to:', data.targetUsername);
      setToast({
        message: 'Đã gửi lời mời thách đấu!',
        type: 'success'
      });
    });

    socket.on('challenge_failed', (data) => {
      console.log('Challenge failed:', data.message);
      setToast({
        message: data.message || 'Gửi thách đấu thất bại',
        type: 'error'
      });
    });

    socket.on('challenge_declined', (data) => {
      console.log('Challenge declined by:', data.responder);
      setToast({
        message: `${data.responder.fullname || data.responder.username} đã từ chối thách đấu`,
        type: 'warning'
      });
    });

    socket.on('game_start', (data) => {
      console.log('Game starting:', data);
      // Redirect to game with gameId
      history.push({
        pathname: '/game',
        state: {
          username: currentUser?.username,
          game: { id: data.gameId }
        }
      });
    });

    // Cleanup
    return () => {
      socket.off('update_online_users');
      socket.off('receive_challenge');
      socket.off('challenge_sent');
      socket.off('challenge_failed');
      socket.off('challenge_declined');
      socket.off('game_start');
    };
  }, [currentUser?.username, history]);

  const fetchUserInfo = async (username) => {
    try {
      const response = await getUser(username);
      if (response.success && response.user) {
        setCurrentUser(response.user);
        // Cập nhật localStorage
        localStorage.setItem('user', JSON.stringify(response.user));
        
        // Emit user_login after fetching user info
        socket.emit('user_login', {
          username: response.user.username,
          fullname: response.user.fullname || response.user.username,
          elo: response.user.elo || 1200
        });
        
        console.log('Emitted user_login:', response.user.username);
      } else {
        // Fallback nếu không fetch được
        const fallbackUser = {
          username: username,
          fullname: username,
          elo: 1200
        };
        setCurrentUser(fallbackUser);
        
        // Emit user_login with fallback data
        socket.emit('user_login', fallbackUser);
      }
    } catch (error) {
      console.error('Error fetching user info:', error);
      const fallbackUser = {
        username: username,
        fullname: username,
        elo: 1200
      };
      setCurrentUser(fallbackUser);
      
      // Emit user_login with fallback data
      socket.emit('user_login', fallbackUser);
    }
  };

  const handleLogout = () => {
    logoutUser();
    history.push('/login');
  };

  const handleChallenge = (opponentUsername) => {
    console.log('Challenge sent to:', opponentUsername);
    
    // Find opponent info
    const opponent = onlineUsers.find(u => u.username === opponentUsername);
    
    // Emit challenge to server
    socket.emit('send_challenge', {
      targetUsername: opponentUsername,
      senderInfo: {
        username: currentUser?.username,
        fullname: currentUser?.fullname,
        elo: currentUser?.elo
      }
    });
  };

  const handleAcceptChallenge = () => {
    console.log('Accepting challenge from:', challengeModal.senderInfo);
    
    socket.emit('respond_challenge', {
      status: 'accepted',
      senderUsername: challengeModal.senderInfo.username,
      responderInfo: {
        username: currentUser?.username,
        fullname: currentUser?.fullname
      }
    });
    
    setChallengeModal({ open: false, senderInfo: null });
  };

  const handleDeclineChallenge = () => {
    console.log('Declining challenge from:', challengeModal.senderInfo);
    
    socket.emit('respond_challenge', {
      status: 'declined',
      senderUsername: challengeModal.senderInfo.username,
      responderInfo: {
        username: currentUser?.username,
        fullname: currentUser?.fullname
      }
    });
    
    setChallengeModal({ open: false, senderInfo: null });
  };

  // Filter out current user from online users list
  const filteredOnlineUsers = onlineUsers.filter(
    user => user.username !== currentUser?.username
  );

  return (
    <div className="home-container">
      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Challenge Modal */}
      <ChallengeModal
        open={challengeModal.open}
        senderInfo={challengeModal.senderInfo}
        onAccept={handleAcceptChallenge}
        onDecline={handleDeclineChallenge}
      />

      {/* Fixed Top Navbar */}
      <div className="navbar-fixed">
        {/* Left: Logo & Title */}
        <div className="navbar-left">
          <Icon name='chess' size='big' className="navbar-icon" />
          <div className="navbar-title">
            <h2>Online Chess</h2>
            <p>Play with friends worldwide</p>
          </div>
        </div>

        {/* Right: User Info & Logout */}
        <div className="navbar-right">
          <div className="user-info-container">
            <div className="user-greeting">
              Xin chào, {currentUser?.fullname || currentUser?.username || 'Guest'}
            </div>
            <div className="user-elo">
              <Icon name='trophy' />
              Elo: {currentUser?.elo || 1200}
            </div>
          </div>
          <Button 
            icon 
            onClick={handleLogout}
            className="logout-button"
          >
            <Icon name='sign out' /> Đăng xuất
          </Button>
        </div>
      </div>

      {/* Main Content Area - Below Navbar */}
      <div className="main-content-wrapper">
        <Grid stackable className="content-grid">
          <Grid.Row>
            {/* Left Column: New Game Action */}
            <Grid.Column width={6}>
              <div className="game-card">
                <Header as='h2' className="game-card-header">
                  <Icon name='gamepad' className="game-card-icon" />
                  <Header.Content>
                    Bắt đầu chơi
                    <Header.Subheader className="game-card-subtitle">
                      Tạo phòng mới hoặc chơi với máy
                    </Header.Subheader>
                  </Header.Content>
                </Header>
                
                <NewGameButtons />
              </div>
            </Grid.Column>

            {/* Right Column: Online Players */}
            <Grid.Column width={10}>
              <div className="players-card">
                <div className="players-header">
                  <div className="players-header-left">
                    <Icon name='users' className="players-header-icon" />
                    <h3 className="players-header-title">Người chơi Online</h3>
                  </div>
                  <span className="online-badge">
                    {filteredOnlineUsers.length} online
                  </span>
                </div>

                {/* Online Players List */}
                <div className="players-list-container">
                  {filteredOnlineUsers.length > 0 ? (
                    <List divided relaxed className="players-list">
                      {filteredOnlineUsers.map((user, index) => (
                        <List.Item 
                          key={index}
                          className={`player-item ${index % 2 === 0 ? 'player-item-even' : 'player-item-odd'}`}
                        >
                          <div className="player-content">
                            {/* Avatar */}
                            <div className="player-avatar">
                              <Icon name='user' size='large' className="player-avatar-icon" />
                            </div>
                            
                            {/* User Info */}
                            <div className="player-details">
                              <div className="player-name">
                                {user.fullname || user.username}
                              </div>
                              <div className="player-rating">
                                <Icon name='trophy' />
                                Elo: {user.elo || 1200}
                              </div>
                            </div>

                            {/* Challenge Button */}
                            <Button
                              color='orange'
                              size='small'
                              onClick={() => handleChallenge(user.username)}
                              className="challenge-button"
                            >
                              <Icon name='bolt' /> Thách đấu
                            </Button>
                          </div>
                        </List.Item>
                      ))}
                    </List>
                  ) : (
                    <div className="empty-players">
                      <Icon name='users' size='huge' className="empty-players-icon" />
                      <p className="empty-players-title">
                        Không có người chơi nào khác đang online
                      </p>
                      <p className="empty-players-subtitle">
                        Hãy mời bạn bè tham gia!
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="main ui">
        {/* Route mặc định redirect đến login */}
        <Route path="/" exact>
          <Redirect to="/login" />
        </Route>

        {/* Routes công khai */}
        <Route path="/login" component={Login} />
        <Route path="/register" component={Register} />

        {/* Routes yêu cầu đăng nhập */}
        <PrivateRoute path="/home" component={HomePage} />
        
        <PrivateRoute path="/game" component={ChessBoard} />
      </div>
    </Router>
  );
}

export default App;
