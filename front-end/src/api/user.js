/**
 * User API
 * Các hàm gọi API liên quan đến user và authentication
 */
import axios from 'axios';

// Cấu hình base URL cho API
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// Tạo axios instance với cấu hình mặc định
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor để tự động thêm token vào headers
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Đăng ký user mới
 * @param {string} fullname - Họ và tên
 * @param {string} username - Tên đăng nhập
 * @param {string} password - Mật khẩu
 * @returns {Promise} Response từ server
 */
export const registerUser = async (fullname, username, password) => {
  try {
    const response = await apiClient.post('/api/auth/register', {
      fullname,
      username,
      password,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { success: false, message: 'Lỗi kết nối server' };
  }
};

/**
 * Đăng nhập
 * @param {string} username - Tên đăng nhập
 * @param {string} password - Mật khẩu
 * @returns {Promise} Response từ server
 */
export const loginUser = async (username, password) => {
  try {
    const response = await apiClient.post('/api/auth/login', {
      username,
      password,
    });
    
    // Lưu thông tin user vào localStorage nếu đăng nhập thành công
    if (response.data.success && response.data.user) {
      localStorage.setItem('user', JSON.stringify(response.data.user));
      // Lưu token nếu có
      if (response.data.token) {
        localStorage.setItem('token', response.data.token);
      }
    }
    
    return response.data;
  } catch (error) {
    throw error.response?.data || { success: false, message: 'Lỗi kết nối server' };
  }
};

/**
 * Lấy thông tin profile của user hiện tại
 * @returns {Promise} Response từ server
 */
export const getUserProfile = async () => {
  try {
    const response = await apiClient.get('/api/auth/profile');
    return response.data;
  } catch (error) {
    throw error.response?.data || { success: false, message: 'Lỗi kết nối server' };
  }
};

/**
 * Lấy thông tin user theo username
 * @param {string} username - Tên đăng nhập
 * @returns {Promise} Response từ server
 */
export const getUser = async (username) => {
  try {
    const response = await apiClient.get('/api/user', {
      params: { username },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { success: false, message: 'Lỗi kết nối server' };
  }
};

/**
 * Lấy danh sách tất cả users
 * @returns {Promise} Response từ server
 */
export const getAllUsers = async () => {
  try {
    const response = await apiClient.get('/api/users');
    return response.data;
  } catch (error) {
    throw error.response?.data || { success: false, message: 'Lỗi kết nối server' };
  }
};

/**
 * Đăng xuất
 */
export const logoutUser = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

/**
 * Kiểm tra xem user đã đăng nhập chưa
 * @returns {boolean} true nếu đã đăng nhập
 */
export const isAuthenticated = () => {
  const token = localStorage.getItem('token');
  return !!token;
};

/**
 * Lấy thông tin user từ localStorage
 * @returns {object|null} Thông tin user hoặc null
 */
export const getCurrentUser = () => {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  }
  return null;
};

export default {
  registerUser,
  loginUser,
  getUserProfile,
  getUser,
  getAllUsers,
  logoutUser,
  isAuthenticated,
  getCurrentUser,
};
