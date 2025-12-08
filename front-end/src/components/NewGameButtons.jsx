import React, { useState } from 'react';
import { Button, Icon, Modal, Form, Radio } from 'semantic-ui-react';
import { Redirect } from 'react-router-dom';
import socket from '../SocketConfig';

function NewGameButtons() {
  const [openModal, setOpenModal] = useState(false);
  const [modalType, setModalType] = useState(''); // 'random' or 'computer'
  const [username, setUsername] = useState('');
  const [ai, setAi] = useState('random');
  const [loading, setLoading] = useState(false);
  const [game, setGame] = useState(null);
  const [redirect, setRedirect] = useState(false);

  const handleRandomMatch = () => {
    setModalType('random');
    setOpenModal(true);
  };

  const handlePlayWithBot = () => {
    setModalType('computer');
    setOpenModal(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (modalType === 'random') {
      socket.off("created");
      socket.emit("create", { username: username });
      setLoading(true);
      socket.once("created", ({ game }) => {
        setGame(game);
        setRedirect(true);
        setLoading(false);
      });
    } else if (modalType === 'computer') {
      socket.off("createdComputerGame");
      socket.emit("createComputerGame", { username: username, ai: ai });
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <Button
          primary
          size='large'
          fluid
          onClick={handleRandomMatch}
          style={{
            backgroundColor: '#4CAF50',
            color: '#fff',
            padding: '18px',
            fontSize: '16px',
            fontWeight: '600'
          }}
        >
          <Icon name='random' /> Ghép ngẫu nhiên
        </Button>

        <Button
          size='large'
          fluid
          onClick={handlePlayWithBot}
          style={{
            backgroundColor: 'transparent',
            border: '2px solid #4CAF50',
            color: '#4CAF50',
            padding: '18px',
            fontSize: '16px',
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
          <Form onSubmit={handleSubmit}>
            <Form.Field>
              <label>Tên người chơi</label>
              <input
                placeholder='Nhập tên của bạn'
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </Form.Field>

            {modalType === 'computer' && (
              <Form.Field>
                <label>Chọn độ khó AI: <strong>{ai}</strong></label>
                <Form.Group inline>
                  <Form.Field>
                    <Radio
                      label='Random'
                      name='aiGroup'
                      value='random'
                      checked={ai === 'random'}
                      onChange={() => setAi('random')}
                    />
                  </Form.Field>
                  <Form.Field>
                    <Radio
                      label='Stockfish 14'
                      name='aiGroup'
                      value='stockfish'
                      checked={ai === 'stockfish'}
                      onChange={() => setAi('stockfish')}
                    />
                  </Form.Field>
                  <Form.Field>
                    <Radio
                      label='Minimax'
                      name='aiGroup'
                      value='minimax'
                      checked={ai === 'minimax'}
                      onChange={() => setAi('minimax')}
                    />
                  </Form.Field>
                  <Form.Field>
                    <Radio
                      label='Minimax + ML'
                      name='aiGroup'
                      value='ml'
                      checked={ai === 'ml'}
                      onChange={() => setAi('ml')}
                    />
                  </Form.Field>
                </Form.Group>
              </Form.Field>
            )}
          </Form>
        </Modal.Content>
        <Modal.Actions>
          <Button onClick={() => setOpenModal(false)}>
            Hủy
          </Button>
          <Button
            positive
            loading={loading}
            disabled={username === ''}
            onClick={handleSubmit}
          >
            <Icon name='play' /> Bắt đầu
          </Button>
        </Modal.Actions>
      </Modal>

      {redirect && (
        <Redirect
          to={{
            pathname: "/game",
            state: { username: username, game: game }
          }}
        />
      )}
    </>
  );
}

export default NewGameButtons;
