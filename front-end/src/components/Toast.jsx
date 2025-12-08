import React from 'react';
import { Message, Icon } from 'semantic-ui-react';

function Toast({ message, type = 'success', onClose }) {
  const [visible, setVisible] = React.useState(true);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      if (onClose) onClose();
    }, 3000);

    return () => clearTimeout(timer);
  }, [onClose]);

  if (!visible) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: '90px',
        left: '20px',
        zIndex: 10000,
        animation: 'slideInLeft 0.3s ease-out'
      }}
    >
      <Message
        success={type === 'success'}
        error={type === 'error'}
        warning={type === 'warning'}
        onDismiss={() => {
          setVisible(false);
          if (onClose) onClose();
        }}
      >
        <Icon name={type === 'success' ? 'check circle' : 'exclamation circle'} />
        {message}
      </Message>
    </div>
  );
}

export default Toast;
