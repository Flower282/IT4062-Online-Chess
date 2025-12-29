import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import Login from '../pages/Login.jsx';
import Register from '../pages/Register.jsx';
import ChessBoard from '../pages/ChessBoard.jsx';
import { isAuthenticated } from '../api/user';

// Component để bảo vệ routes yêu cầu đăng nhập
// Note: Token verification sẽ được thực hiện trong component chính (HomePage)
// để tránh duplicate verification
export function PrivateRoute({ component: Component, ...rest }) {
  // Chỉ kiểm tra xem có token không (không verify ở đây)
  const hasToken = isAuthenticated();
  
  return (
    <Route
      {...rest}
      render={(props) =>
        hasToken ? (
          <Component {...props} />
        ) : (
          <Redirect to="/login" />
        )
      }
    />
  );
}

// Export routes configuration
export const routes = {
  public: [
    { path: '/login', component: Login, exact: true },
    { path: '/register', component: Register, exact: true },
  ],
  private: [
    { path: '/game', component: ChessBoard },
  ],
};

export { Login, Register, ChessBoard };
