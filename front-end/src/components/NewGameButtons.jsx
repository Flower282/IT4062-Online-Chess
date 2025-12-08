import React, { useState, useEffect } from 'react';
import { Button, Icon, Modal } from 'semantic-ui-react';
import { Redirect } from 'react-router-dom';
import socket from '../SocketConfig';
import { getCurrentUser } from '../api/user';

const difficultyOptions = [
  { level: 1, label: 'Dễ', description: 'Phù hợp cho người mới bắt đầu' },
  { level: 2, label: 'Trung bình', description: 'Đòi hỏi kỹ năng cơ bản' },
  { level: 3, label: 'Khó', description: 'Thử thách cho người chơi có kinh nghiệm' },
  { level: 4, label: 'Siêu khó', description: 'Rất khó để đánh bại' },
  { level: 5, label: 'Cao thủ', description: 'Chỉ dành cho chuyên gia' }
];

function NewGameButtons() {
  const [openModal, setOpenModal] = useState(false);
  const [modalType, setModalType] = useState(''); // 'random' or 'computer'
  const [username, setUsername] = useState('');
  const [selectedLevel, setSelectedLevel] = useState(1); // Default: Dễ
  const [loading, setLoading] = useState(false);
  const [game, setGame] = useState(null);
  const [redirect, setRedirect] = useState(false);
  
  // Random match searching states
  const [isSearching, setIsSearching] = useState(false);
  const [searchTimer, setSearchTimer] = useState(0);
  const [matchFound, setMatchFound] = useState(false);
  const [matchData, setMatchData] = useState(null); // Store player1, player2, roomId

  // Timer effect for searching
  useEffect(() => {
    let interval;
    if (isSearching && !matchFound) {
      interval = setInterval(() => {
        setSearchTimer(prev => prev + 1);
      }, 1000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSearching, matchFound]);

  // Format seconds to mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleRandomMatch = () => {
    setModalType('random');
    setOpenModal(true);
    setIsSearching(true);
    setSearchTimer(0);
    setMatchFound(false);
    setMatchData(null);
    
    // Get current user info
    const currentUser = getCurrentUser();
    const userInfo = {
      username: currentUser?.username || 'Player',
      fullname: currentUser?.fullname || currentUser?.username || 'Player',
      elo: currentUser?.elo || 1200
    };
    
    // Emit find_match event
    socket.off("match_found");
    socket.off("created");
    socket.emit("find_match", userInfo);
    
    // Listen for match_found event
    socket.once("match_found", (data) => {
      console.log('Match found:', data);
      setMatchFound(true);
      setMatchData(data); // { player1, player2, roomId }
      
      // Auto-redirect after 3 seconds
      setTimeout(() => {
        setGame({ id: data.roomId });
        setRedirect(true);
        setIsSearching(false);
      }, 3000);
    });
    
    // Fallback: Listen for old 'created' event (backward compatibility)
    socket.once("created", ({ game }) => {
      console.log('Game created (old flow):', game);
      setMatchFound(true);
      setGame(game);
      
      setTimeout(() => {
        setRedirect(true);
        setIsSearching(false);
      }, 1500);
    });
  };

  const handleCancelSearch = () => {
    // Emit cancel_match event
    socket.emit('cancel_match');
    
    setIsSearching(false);
    setSearchTimer(0);
    setMatchFound(false);
    setMatchData(null);
    setOpenModal(false);
    socket.off("created");
    socket.off("match_found");
  };

  const handlePlayWithBot = () => {
    setModalType('computer');
    setOpenModal(true);
  };

  const handleSubmit = () => {
    const currentUser = getCurrentUser();
    const usernameToUse = modalType === 'random' 
      ? username 
      : (currentUser?.username || 'Player');
    
    if (modalType === 'random') {
      socket.off("created");
      socket.emit("create", { username: usernameToUse });
      setLoading(true);
      socket.once("created", ({ game }) => {
        setGame(game);
        setRedirect(true);
        setLoading(false);
      });
    } else if (modalType === 'computer') {
      socket.off("createdComputerGame");
      socket.emit("createComputerGame", { 
        username: usernameToUse, 
        ai: 'stockfish'
      });
      setLoading(true);
      socket.once("createdComputerGame", ({ game }) => {
        setGame(game);
        setRedirect(true);
        setLoading(false);
      });
    }
  };

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <Button
          primary
          size='medium'
          fluid
          onClick={handleRandomMatch}
          style={{
            backgroundColor: '#4CAF50',
            color: '#fff',
            padding: '14px',
            fontSize: '15px',
            fontWeight: '600'
          }}
        >
          <Icon name='random' /> Ghép ngẫu nhiên
        </Button>

        <Button
          size='medium'
          fluid
          onClick={handlePlayWithBot}
          style={{
            backgroundColor: 'transparent',
            border: '2px solid #4CAF50',
            color: '#4CAF50',
            padding: '14px',
            fontSize: '15px',
            fontWeight: '600'
          }}
        >
          <Icon name='laptop' /> Chơi với máy
        </Button>
      </div>

      <Modal
        open={openModal}
        onClose={() => setOpenModal(false)}
        size='small'
      >
        <Modal.Header>
          {modalType === 'random' ? 'Ghép ngẫu nhiên' : 'Chơi với máy'}
        </Modal.Header>
        <Modal.Content>
          {modalType === 'random' ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '30px 20px',
              gap: '16px',
              minHeight: '240px',
              justifyContent: 'center'
            }}>
              {matchFound && matchData ? (
                // State 2: Match Found - VS Screen
                <>
                  <div style={{
                    fontSize: '16px',
                    fontWeight: '600',
                    color: '#4CAF50',
                    textAlign: 'center',
                    marginBottom: '8px'
                  }}>
                    Đã tìm thấy trận đấu!
                  </div>
                  
                  {/* VS Layout */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    gap: '16px',
                    padding: '16px 0'
                  }}>
                    {/* Player 1 (Current User) */}
                    <div style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '10px'
                    }}>
                      <div style={{
                        width: '70px',
                        height: '70px',
                        borderRadius: '50%',
                        border: '3px solid #4CAF50',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#F0FDF4',
                        boxShadow: '0 4px 12px rgba(76, 175, 80, 0.3)'
                      }}>
                        <Icon name='user' size='large' style={{ color: '#4CAF50', margin: 0 }} />
                      </div>
                      <div style={{
                        textAlign: 'center'
                      }}>
                        <div style={{
                          fontSize: '15px',
                          fontWeight: '700',
                          color: '#111827',
                          marginBottom: '4px'
                        }}>
                          {matchData.player1?.fullname || matchData.player1?.username}
                        </div>
                        <div style={{
                          fontSize: '13px',
                          color: '#6B7280',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px'
                        }}>
                          <Icon name='trophy' style={{ margin: 0 }} />
                          {matchData.player1?.elo || 1200}
                        </div>
                      </div>
                    </div>

                    {/* VS Badge */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '6px'
                    }}>
                      <div style={{
                        fontSize: '30px',
                        fontWeight: '900',
                        color: '#FFFFFF',
                        background: 'linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%)',
                        padding: '10px 20px',
                        borderRadius: '10px',
                        boxShadow: '0 6px 20px rgba(255, 107, 107, 0.4)',
                        letterSpacing: '2px',
                        transform: 'rotate(-5deg)'
                      }}>
                        VS
                      </div>
                    </div>

                    {/* Player 2 (Opponent) */}
                    <div style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: '10px'
                    }}>
                      <div style={{
                        width: '70px',
                        height: '70px',
                        borderRadius: '50%',
                        border: '3px solid #FF6B6B',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#FEE2E2',
                        boxShadow: '0 4px 12px rgba(255, 107, 107, 0.3)'
                      }}>
                        <Icon name='user' size='large' style={{ color: '#FF6B6B', margin: 0 }} />
                      </div>
                      <div style={{
                        textAlign: 'center'
                      }}>
                        <div style={{
                          fontSize: '15px',
                          fontWeight: '700',
                          color: '#111827',
                          marginBottom: '4px'
                        }}>
                          {matchData.player2?.fullname || matchData.player2?.username}
                        </div>
                        <div style={{
                          fontSize: '13px',
                          color: '#6B7280',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '4px'
                        }}>
                          <Icon name='trophy' style={{ margin: 0 }} />
                          {matchData.player2?.elo || 1200}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Countdown Message */}
                  <div style={{
                    fontSize: '14px',
                    color: '#6B7280',
                    textAlign: 'center',
                    marginTop: '8px'
                  }}>
                    Vào game sau 3s...
                  </div>
                </>
              ) : matchFound ? (
                // Fallback: Old flow success state
                <>
                  <Icon 
                    name='check circle' 
                    size='huge' 
                    style={{ 
                      color: '#4CAF50',
                      animation: 'scaleIn 0.3s ease-out'
                    }} 
                  />
                  <div style={{
                    fontSize: '24px',
                    fontWeight: '700',
                    color: '#4CAF50',
                    textAlign: 'center'
                  }}>
                    Ghép trận thành công!
                  </div>
                  <div style={{
                    fontSize: '14px',
                    color: '#6B7280',
                    textAlign: 'center'
                  }}>
                    Đang chuyển đến bàn cờ...
                  </div>
                </>
              ) : (
                // State 1: Searching with Radar Animation
                <>
                  {/* Radar/Circular Animation */}
                  <div style={{
                    position: 'relative',
                    width: '100px',
                    height: '100px'
                  }}>
                    {/* Outer pulse ring */}
                    <div style={{
                      position: 'absolute',
                      width: '100px',
                      height: '100px',
                      borderRadius: '50%',
                      border: '3px solid #4CAF50',
                      opacity: 0.3,
                      animation: 'pulse 2s ease-out infinite'
                    }} />
                    {/* Middle pulse ring */}
                    <div style={{
                      position: 'absolute',
                      width: '100px',
                      height: '100px',
                      borderRadius: '50%',
                      border: '3px solid #4CAF50',
                      opacity: 0.5,
                      animation: 'pulse 2s ease-out 0.5s infinite'
                    }} />
                    {/* Center spinning icon */}
                    <div style={{
                      position: 'absolute',
                      width: '100px',
                      height: '100px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Icon 
                        name='sync' 
                        loading 
                        size='big' 
                        style={{ color: '#4CAF50', margin: 0 }} 
                      />
                    </div>
                  </div>
                  
                  <div style={{
                    fontSize: '18px',
                    fontWeight: '600',
                    color: '#111827',
                    textAlign: 'center'
                  }}>
                    Đang tìm đối thủ...
                  </div>
                  
                  {/* Timer */}
                  <div style={{
                    fontSize: '40px',
                    fontWeight: '700',
                    color: '#4CAF50',
                    fontFamily: 'monospace',
                    letterSpacing: '3px'
                  }}>
                    {formatTime(searchTimer)}
                  </div>
                  
                  <div style={{
                    fontSize: '12px',
                    color: '#9CA3AF',
                    textAlign: 'center'
                  }}>
                    Vui lòng chờ trong giây lát...
                  </div>
                </>
              )}
            </div>
          ) : (
            <div>
              <label style={{ 
                display: 'block', 
                marginBottom: '12px',
                fontSize: '15px',
                fontWeight: '600',
                color: '#111827'
              }}>Chọn độ khó</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {difficultyOptions.map((option) => (
                  <div
                    key={option.level}
                    onClick={() => setSelectedLevel(option.level)}
                    style={{
                      padding: '12px 16px',
                      border: selectedLevel === option.level 
                        ? '2px solid #4CAF50' 
                        : '2px solid #E5E7EB',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      backgroundColor: selectedLevel === option.level 
                        ? '#F0FDF4' 
                        : '#FFFFFF',
                      transition: 'all 0.2s ease',
                      boxShadow: selectedLevel === option.level 
                        ? '0 2px 8px rgba(76, 175, 80, 0.15)' 
                        : '0 1px 3px rgba(0, 0, 0, 0.1)'
                    }}
                    onMouseEnter={(e) => {
                      if (selectedLevel !== option.level) {
                        e.currentTarget.style.borderColor = '#9CA3AF';
                        e.currentTarget.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.12)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (selectedLevel !== option.level) {
                        e.currentTarget.style.borderColor = '#E5E7EB';
                        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
                      }
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div>
                        <div style={{ 
                          fontSize: '15px', 
                          fontWeight: '600',
                          color: '#111827',
                          marginBottom: '2px'
                        }}>
                          {option.label}
                        </div>
                        <div style={{ 
                          fontSize: '12px', 
                          color: '#6B7280'
                        }}>
                          {option.description}
                        </div>
                      </div>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        border: selectedLevel === option.level 
                          ? '2px solid #4CAF50' 
                          : '2px solid #D1D5DB',
                        backgroundColor: selectedLevel === option.level 
                          ? '#4CAF50' 
                          : '#FFFFFF'
                      }}>
                        {selectedLevel === option.level && (
                          <Icon name='check' style={{ color: '#FFFFFF', margin: 0 }} />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Modal.Content>
        <Modal.Actions>
          {modalType === 'random' ? (
            // Random Match: Show Cancel button only after 5 seconds, centered
            searchTimer >= 5 && !matchFound ? (
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                width: '100%'
              }}>
                <Button 
                  color='red'
                  onClick={handleCancelSearch}
                  style={{
                    maxWidth: '200px',
                    width: '100%'
                  }}
                >
                  <Icon name='cancel' /> Hủy tìm kiếm
                </Button>
              </div>
            ) : null
          ) : (
            // Computer Match: Show normal buttons
            <>
              <Button onClick={() => setOpenModal(false)}>
                Hủy
              </Button>
              <Button
                positive
                loading={loading}
                onClick={handleSubmit}
              >
                <Icon name='play' /> Bắt đầu
              </Button>
            </>
          )}
        </Modal.Actions>
      </Modal>

      {redirect && (
        <Redirect
          to={{
            pathname: "/game",
            state: { 
              username: getCurrentUser()?.username || 'Player', 
              game: game 
            }
          }}
        />
      )}
    </>
  );
}

export default NewGameButtons;
