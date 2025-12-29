import React, { useState, useEffect } from 'react';
import './css/App.css';
import { BrowserRouter as Router, Route, Redirect } from 'react-router-dom';
import { Header, Icon, Card, List, Segment, Grid, Button } from 'semantic-ui-react';
import { PrivateRoute, Login, Register, ChessBoard } from './routes/router';
import NewGameButtons from './components/NewGameButtons.jsx';
import Toast from './components/Toast.jsx';
import ChallengeModal from './components/ChallengeModal.jsx';
import { getCurrentUser, getAllUsers, getUser, logoutUser, verifyToken, isAuthenticated } from './api/user';
import { useHistory } from 'react-router-dom';
import socket from './SocketConfig';

// Component trang chủ sau khi đăng nhập
function HomePage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [toast, setToast] = useState(null);
  const [challengeModal, setChallengeModal] = useState({ open: false, senderInfo: null });
  const [loading, setLoading] = useState(true);
  const [waitingForResponse, setWaitingForResponse] = useState(false); // Track if waiting for challenge response
  const history = useHistory();

  useEffect(() => {
    // Token persistence: Verify token khi app load
    const initializeAuth = async () => {
      try {
        console.log('=== INITIALIZING AUTH ===');
        
        // Kiểm tra xem có token không
        if (isAuthenticated()) {
          console.log('Token found in localStorage');
          
          // Small delay to ensure localStorage is fully written
          await new Promise(resolve => setTimeout(resolve, 50));
          
          try {
            // Gọi API verify token
            console.log('Calling verifyToken API...');
            const response = await verifyToken();
            
            if (response.success && response.user) {
              console.log('✓ Token valid, user:', response.user);
              setCurrentUser(response.user);
              
              // Cập nhật localStorage với thông tin mới nhất
              localStorage.setItem('user', JSON.stringify(response.user));
              
              // Emit user_login to server
              socket.emit('user_login', {
                username: response.user.username,
                fullname: response.user.fullname || response.user.username,
                elo: response.user.elo || 1200
              });
              
              console.log('✓ Emitted user_login:', response.user.username);
            } else {
              // Token không hợp lệ, redirect về login
              console.log('✗ Token invalid, redirecting to login');
              localStorage.removeItem('token');
              localStorage.removeItem('user');
              history.push('/login');
            }
          } catch (verifyError) {
            console.error('Token verification failed:', verifyError);
            // Token có thể hết hạn hoặc không hợp lệ
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            history.push('/login');
          }
        } else {
          // Không có token
          console.log('✗ No token found, redirecting to login');
          localStorage.removeItem('user');
          history.push('/login');
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        history.push('/login');
      } finally {
        setLoading(false);
      }
    };
    
    initializeAuth();

    // Listen for real-time online users updates from server
    socket.on('update_online_users', (data) => {
      console.log('Received update_online_users:', data);
      if (data.users) {
        setOnlineUsers(data.users);
      }
    });

    // Socket listeners for challenge feature
    socket.on('receive_challenge', (data) => {
      console.log('=== RECEIVE_CHALLENGE EVENT ===');
      console.log('Received challenge:', data);
      console.log('Current user:', currentUser?.username);
      console.log('Sender:', data.senderInfo?.username);
      console.log('Should show modal:', data.senderInfo?.username !== currentUser?.username);
      
      // Only show modal if the challenge is NOT from yourself
      if (data.senderInfo?.username !== currentUser?.username) {
        setChallengeModal({
          open: true,
          senderInfo: data.senderInfo
        });
      } else {
        console.warn('Received challenge from self - ignoring');
      }
    });

    socket.on('challenge_sent', (data) => {
      console.log('=== CHALLENGE_SENT EVENT ===');
      console.log('Challenge sent to:', data.targetUsername);
      console.log('Waiting for response from opponent...');
      setWaitingForResponse(true); // Set waiting state
      setToast({
        message: 'Đã gửi lời mời thách đấu! Đang chờ phản hồi...',
        type: 'success'
      });
    });

    socket.on('challenge_failed', (data) => {
      console.log('=== CHALLENGE_FAILED EVENT ===');
      console.log('Challenge failed:', data.message);
      setWaitingForResponse(false); // Clear waiting state
      setToast({
        message: data.message || 'Gửi thách đấu thất bại',
        type: 'error'
      });
    });

    socket.on('challenge_declined', (data) => {
      console.log('=== CHALLENGE_DECLINED EVENT ===');
      console.log('Challenge declined by:', data.responder);
      setWaitingForResponse(false); // Clear waiting state
      setToast({
        message: `${data.responder.fullname || data.responder.username} đã từ chối thách đấu`,
        type: 'warning'
      });
    });
    
    socket.on('challenge_error', (data) => {
      console.log('=== CHALLENGE_ERROR EVENT ===');
      console.log('Challenge error:', data.message);
      setWaitingForResponse(false); // Clear waiting state
      setToast({
        message: data.message || 'Lỗi trong quá trình thách đấu',
        type: 'error'
      });
    });

    socket.on('game_start', (data) => {
      console.log('=== GAME_START EVENT ===');
      console.log('Game starting:', data);
      console.log('Game ID:', data.gameId);
      console.log('Game object:', data.game);
      console.log('Opponent:', data.opponent);
      console.log('Current user:', currentUser);
      
      setWaitingForResponse(false); // Clear waiting state
      
      // Validate data
      if (!data.game || !data.game.id) {
        console.error('ERROR: Invalid game data received!');
        setToast({
          message: 'Lỗi khi tạo phòng chơi',
          type: 'error'
        });
        return;
      }
      
      console.log('✓ Redirecting to game...');
      
      // Redirect to game with full game object
      history.push({
        pathname: '/game',
        state: {
          username: currentUser?.username,
          game: data.game
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
      socket.off('challenge_error');
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
    console.log('=== HANDLE_CHALLENGE ===');
    console.log('Challenge sent to:', opponentUsername);
    console.log('Current user:', currentUser?.username);
    console.log('Current user fullname:', currentUser?.fullname);
    
    // Find opponent info
    const opponent = onlineUsers.find(u => u.username === opponentUsername);
    console.log('Opponent found:', opponent);
    
    // Emit challenge to server
    socket.emit('send_challenge', {
      targetUsername: opponentUsername,
      senderInfo: {
        username: currentUser?.username,
        fullname: currentUser?.fullname,
        elo: currentUser?.elo
      }
    });
    
    console.log('Emitted send_challenge to server');
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

  // Show loading while verifying token
  if (loading) {
    return (
      <div className="home-container" style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div style={{ textAlign: 'center' }}>
          <Icon name='chess' size='huge' loading style={{ color: '#4CAF50' }} />
          <Header as='h3' style={{ marginTop: '20px', color: '#111827' }}>
            Đang xác thực...
          </Header>
        </div>
      </div>
    );
  }

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
      
      {/* Waiting for Response Modal */}
      {waitingForResponse && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: '#FFFFFF',
            padding: '40px',
            borderRadius: '12px',
            textAlign: 'center',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
            maxWidth: '400px'
          }}>
            <Icon name='hourglass half' size='huge' loading style={{ color: '#FF9800' }} />
            <Header as='h3' style={{ marginTop: '20px', color: '#111827' }}>
              Đang chờ phản hồi...
            </Header>
            <p style={{ color: '#6B7280', marginTop: '10px' }}>
              Đối thủ đang xem xét lời thách đấu của bạn
            </p>
            <Button
              onClick={() => setWaitingForResponse(false)}
              style={{
                marginTop: '20px',
                backgroundColor: '#EF4444',
                color: '#fff'
              }}
            >
              Hủy
            </Button>
          </div>
        </div>
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
