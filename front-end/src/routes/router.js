import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import Login from '../pages/Login.jsx';
import Register from '../pages/Register.jsx';
import ChessBoard from '../pages/ChessBoard.jsx';

// Component để bảo vệ routes yêu cầu đăng nhập
export function PrivateRoute({ component: Component, ...rest }) {
  const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
  
  return (
    <Route
      {...rest}
      render={(props) =>
        isLoggedIn ? (
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
