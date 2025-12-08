import React, { useState, useEffect, useRef } from 'react';
import { Link, Redirect } from 'react-router-dom';
import { Form, Button, Message, Container, Header, Segment } from 'semantic-ui-react';
import { loginUser } from '../api/user';
import '../css/Login.css';

function Login() {
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [redirect, setRedirect] = useState(false);
	const [loading, setLoading] = useState(false);
	const isMounted = useRef(true);

	useEffect(() => {
		// Cleanup function để đánh dấu component đã unmount
		return () => {
			isMounted.current = false;
		};
	}, []);

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
				// Lưu thông tin user vào localStorage
				localStorage.setItem('username', username);
				localStorage.setItem('isLoggedIn', 'true');
				setRedirect(true);
			} else {
				setError(response.message || 'Đăng nhập thất bại');
			}
		} catch (error) {
			// Chỉ cập nhật state nếu component vẫn mounted
			if (!isMounted.current) return;
			setError(error.message || 'Lỗi kết nối server');
		} finally {
			// Chỉ cập nhật state nếu component vẫn mounted
			if (isMounted.current) {
				setLoading(false);
			}
		}
	};

	if (redirect) {
		return <Redirect to="/home" />;
	}

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
