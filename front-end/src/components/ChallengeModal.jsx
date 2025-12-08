import React from 'react';
import { Modal, Button, Icon, Header } from 'semantic-ui-react';

function ChallengeModal({ open, senderInfo, onAccept, onDecline }) {
  return (
    <Modal
      open={open}
      size='small'
      style={{ textAlign: 'center' }}
    >
      <Modal.Header>
        <Icon name='trophy' color='orange' />
        Lời mời thách đấu
      </Modal.Header>
      <Modal.Content>
        <Header as='h3' style={{ color: '#111827' }}>
          Người chơi <strong>{senderInfo?.fullname || senderInfo?.username}</strong> muốn thách đấu bạn!
        </Header>
        {senderInfo?.elo && (
          <p style={{ color: '#6B7280', fontSize: '16px', marginTop: '10px' }}>
            <Icon name='trophy' />
            Elo: {senderInfo.elo}
          </p>
        )}
      </Modal.Content>
      <Modal.Actions style={{ display: 'flex', justifyContent: 'center', gap: '15px' }}>
        <Button
          size='large'
          onClick={onDecline}
          style={{
            backgroundColor: 'transparent',
            border: '2px solid #EF4444',
            color: '#EF4444',
            minWidth: '120px'
          }}
        >
          <Icon name='close' /> Từ chối
        </Button>
        <Button
          size='large'
          positive
          onClick={onAccept}
          style={{
            backgroundColor: '#4CAF50',
            color: '#fff',
            minWidth: '120px'
          }}
        >
          <Icon name='check' /> Đồng ý
        </Button>
      </Modal.Actions>
    </Modal>
  );
}

export default ChallengeModal;
