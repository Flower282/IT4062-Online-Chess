import React, { useState, useEffect, useRef } from 'react';
import { Link, useHistory } from 'react-router-dom';
import { Form, Button, Message, Container, Header, Segment } from 'semantic-ui-react';
import { loginUser, isAuthenticated } from '../api/user';
import '../css/Login.css';

function Login() {
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [loading, setLoading] = useState(false);
	const [isLoggedIn, setIsLoggedIn] = useState(false);
	const isMounted = useRef(true);
	const history = useHistory();

	useEffect(() => {
		// Check if already logged in
		if (isAuthenticated()) {
			console.log('Already authenticated, redirecting to home');
			history.push('/home');
		}
		
		// Cleanup function
		return () => {
			isMounted.current = false;
		};
	}, [history]);
	
	// Separate useEffect to handle redirect after successful login
	useEffect(() => {
		if (isLoggedIn && isAuthenticated()) {
			console.log('Login state changed, token verified, redirecting...');
			// Small delay to ensure token is fully saved
			const timer = setTimeout(() => {
				history.push('/home');
			}, 100);
			return () => clearTimeout(timer);
		}
	}, [isLoggedIn, history]);

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError('');

		if (!username || !password) {
			setError('Vui lòng điền đầy đủ thông tin');
			return;
		}

		setLoading(true);

		try {
			// Gọi API đăng nhập
			const response = await loginUser(username, password);
			
			// Chỉ cập nhật state nếu component vẫn mounted
			if (!isMounted.current) return;
			
			if (response.success) {
				console.log('Login successful, token:', response.token);
				console.log('User data:', response.user);
				
				// Verify token is saved before setting login state
				await new Promise(resolve => setTimeout(resolve, 50));
				
				if (isAuthenticated()) {
					console.log('Token verified in localStorage');
					setIsLoggedIn(true);
				} else {
					console.error('Token not found after login!');
					setError('Lỗi lưu phiên đăng nhập. Vui lòng thử lại.');
				}
			} else {
				setError(response.message || 'Đăng nhập thất bại');
			}
		} catch (error) {
			// Chỉ cập nhật state nếu component vẫn mounted
			if (!isMounted.current) return;
			setError(error.message || 'Lỗi kết nối server');
			console.error('Login error:', error);
		} finally {
			// Chỉ cập nhật state nếu component vẫn mounted
			if (isMounted.current) {
				setLoading(false);
			}
		}
	};

	return (
		<Container className="login-container">
			<Segment className="login-segment">
				<Header as="h2" textAlign="center" className="login-header">
					Đăng nhập
				</Header>
				
				{error && <Message negative>{error}</Message>}

				<Form onSubmit={handleSubmit}>
					<Form.Field>
						<label>Tên đăng nhập</label>
						<input
							placeholder="Nhập tên đăng nhập"
							value={username}
							onChange={(e) => setUsername(e.target.value)}
						/>
					</Form.Field>

					<Form.Field>
						<label>Mật khẩu</label>
						<input
							type="password"
							placeholder="Nhập mật khẩu"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
						/>
					</Form.Field>

					<Button
						type="submit"
						primary
						fluid
						loading={loading}
						disabled={loading}
						className="login-button"
					>
						Đăng nhập
					</Button>
				</Form>

				<div className="register-link">
					Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link>
				</div>
			</Segment>
		</Container>
	);
}

export default Login;
