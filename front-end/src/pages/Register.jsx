import React, { useState, useEffect, useRef } from 'react';
import { Link, Redirect } from 'react-router-dom';
import { Form, Button, Message, Container, Header, Segment } from 'semantic-ui-react';
import { registerUser } from '../api/user';
import '../css/Register.css';

function Register() {
	const [fullName, setFullName] = useState('');
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [confirmPassword, setConfirmPassword] = useState('');
	const [error, setError] = useState('');
	const [success, setSuccess] = useState(false);
	const [redirect, setRedirect] = useState(false);
	const [loading, setLoading] = useState(false);
	const isMounted = useRef(true);
	const timeoutId = useRef(null);

	useEffect(() => {
		// Cleanup function
		return () => {
			isMounted.current = false;
			// Clear timeout nếu component unmount
			if (timeoutId.current) {
				clearTimeout(timeoutId.current);
			}
		};
	}, []);

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError('');
		setSuccess(false);

		// Validation
		if (!fullName || !username || !password || !confirmPassword) {
			setError('Vui lòng điền đầy đủ thông tin');
			return;
		}

		if (username.length < 3) {
			setError('Tên đăng nhập phải có ít nhất 3 ký tự');
			return;
		}

		if (password.length < 6) {
			setError('Mật khẩu phải có ít nhất 6 ký tự');
			return;
		}

		if (password !== confirmPassword) {
			setError('Mật khẩu xác nhận không khớp');
			return;
		}

		setLoading(true);

		try {
			// Gọi API đăng ký
			const response = await registerUser(fullName, username, password);
			
			// Chỉ cập nhật state nếu component vẫn mounted
			if (!isMounted.current) return;
			
			if (response.success) {
				setSuccess(true);
				
				// Redirect sau 2 giây
				timeoutId.current = setTimeout(() => {
					if (isMounted.current) {
						setRedirect(true);
					}
				}, 2000);
			} else {
				setError(response.message || 'Đăng ký thất bại');
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
		return <Redirect to="/login" />;
	}

	return (
		<Container className="register-container">
			<Segment className="register-segment">
				<Header as="h2" textAlign="center" className="register-header">
					Đăng ký tài khoản
				</Header>
				
				{error && <Message negative>{error}</Message>}
				{success && <Message positive>Đăng ký thành công! Đang chuyển đến trang đăng nhập...</Message>}

				<Form onSubmit={handleSubmit}>
					<Form.Field>
						<label>Họ và tên</label>
						<input
							placeholder="Nhập họ và tên"
							value={fullName}
							onChange={(e) => setFullName(e.target.value)}
						/>
					</Form.Field>

					<Form.Field>
						<label>Tên đăng nhập</label>
						<input
							placeholder="Nhập tên đăng nhập (ít nhất 3 ký tự)"
							value={username}
							onChange={(e) => setUsername(e.target.value)}
						/>
					</Form.Field>

					<Form.Field>
						<label>Mật khẩu</label>
						<input
							type="password"
							placeholder="Nhập mật khẩu (ít nhất 6 ký tự)"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
						/>
					</Form.Field>

					<Form.Field>
						<label>Xác nhận mật khẩu</label>
						<input
							type="password"
							placeholder="Nhập lại mật khẩu"
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
						/>
					</Form.Field>

					<Button
						type="submit"
						primary
						fluid
						loading={loading}
						disabled={loading || success}
						className="register-button"
					>
						Đăng ký
					</Button>
				</Form>

				<div className="login-link">
					Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
				</div>
			</Segment>
		</Container>
	);
}

export default Register;
