import React, { useEffect, useState } from 'react';
import { Button, Icon, Header } from 'semantic-ui-react';
import Popup from 'reactjs-popup';
import { useHistory } from 'react-router-dom';
import "./css/NewGamePopup.css";

function WinLostPopup(props) {
    const [open, setOpen] = useState(undefined)
    const [win, setWin] = useState(props.win)
    const [lost, setLost] = useState(props.lost)
    const [draw, setDraw] = useState(props.draw)
    const [resigned, setResigned] = useState(props.resigned)
    const history = useHistory();

    useEffect(() => {
        if (props.win || props.lost || props.draw) {
            setOpen(true)
        }
        setWin(props.win)
        setLost(props.lost)
        setDraw(props.draw)
        setResigned(props.resigned)
        
    }, [props.win, props.lost, props.draw, props.resigned])

    const renderMessage = () => {
        if (win) {
            return {
                title: "Chiến thắng!",
                subtitle: resigned ? "Đối thủ đã xin thua" : "Bạn đã thắng ván này",
                icon: "trophy",
                color: "#4CAF50"
            }
        } else if (lost) {
            return {
                title: "Thất bại",
                subtitle: resigned ? "Bạn đã xin thua" : "Đối thủ đã thắng",
                icon: "frown outline",
                color: "#FF6B6B"
            }
        } else if (draw) {
            return {
                title: "Hòa",
                subtitle: "Ván đấu kết thúc hòa",
                icon: "handshake outline",
                color: "#FF9800"
            }
        }
        return { title: "", subtitle: "", icon: "chess", color: "#111827" }
    }

    const handleClose = () => {
        setOpen(false);
        setWin(false);
        setLost(false);
        setDraw(false);
        history.push('/home');
    }

    const messageData = renderMessage();

    return (
        <Popup 
            open={open} 
            onClose={handleClose}
            modal
            closeOnDocumentClick={false}
            closeOnEscape={false}
            overlayStyle={{
                background: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}
            contentStyle={{
                width: 'auto',
                padding: 0,
                border: 'none',
                background: 'transparent'
            }}
        >
            <div style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '12px',
                padding: '40px',
                textAlign: 'center',
                maxWidth: '450px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
            }}>
                {/* Icon */}
                <div style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '50%',
                    backgroundColor: `${messageData.color}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 20px'
                }}>
                    <Icon 
                        name={messageData.icon} 
                        size='huge' 
                        style={{ color: messageData.color, margin: 0 }} 
                    />
                </div>

                {/* Title */}
                <Header 
                    as='h2' 
                    style={{ 
                        color: '#111827',
                        marginBottom: '10px',
                        fontWeight: 700,
                        textAlign: 'center'
                    }}
                >
                    {messageData.title}
                </Header>

                {/* Subtitle */}
                <p style={{
                    color: '#6B7280',
                    fontSize: '16px',
                    marginBottom: '30px',
                    textAlign: 'center'
                }}>
                    {messageData.subtitle}
                </p>

                {/* Back to Home Button */}
                <Button
                    size='large'
                    onClick={handleClose}
                    style={{
                        backgroundColor: '#4CAF50',
                        color: '#FFFFFF',
                        padding: '12px 30px',
                        borderRadius: '8px',
                        fontWeight: 600,
                        border: 'none',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={(e) => {
                        e.target.style.backgroundColor = '#45a049';
                        e.target.style.transform = 'translateY(-2px)';
                        e.target.style.boxShadow = '0 4px 12px rgba(76, 175, 80, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                        e.target.style.backgroundColor = '#4CAF50';
                        e.target.style.transform = 'translateY(0)';
                        e.target.style.boxShadow = 'none';
                    }}
                >
                    <Icon name='check' /> OK
                </Button>
            </div>
        </Popup >
    );
}

export default WinLostPopup;
