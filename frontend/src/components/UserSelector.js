import React, { useState, useEffect } from 'react';
import { userAPI, setAuthToken, getAuthToken } from '../services/api';

const UserSelector = ({ currentUser, onUserChange, onAuthStatusChange }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '' });
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      fetchUsers();
    }
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await userAPI.getAll();
      setUsers(response.data);
    } catch (err) {
      setError('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await userAPI.create(newUser);
      setUsers([...users, response.data]);
      setNewUser({ username: '', email: '', password: '' });
      setShowCreateForm(false);
      setSuccess('用户创建成功！请使用新账号登录');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || '创建用户失败');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await userAPI.login(loginData);
      const { access_token } = response.data;
      setAuthToken(access_token);
      
      const usersResponse = await userAPI.getAll();
      setUsers(usersResponse.data);
      
      const currentUserData = usersResponse.data.find(
        u => u.username === loginData.username
      );
      
      if (currentUserData) {
        onUserChange(currentUserData);
        onAuthStatusChange(true);
      }
      
      setLoginData({ username: '', password: '' });
      setShowLoginForm(false);
      setSuccess('登录成功！');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败');
    }
  };

  const handleLogout = () => {
    setAuthToken(null);
    onUserChange(null);
    onAuthStatusChange(false);
    setSuccess('已登出');
    setTimeout(() => setSuccess(''), 3000);
  };

  return (
    <div className="card">
      <h2>用户认证</h2>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {currentUser ? (
        <div className="current-user">
          <h3>当前用户: {currentUser.username}</h3>
          <p>邮箱: {currentUser.email}</p>
          <button 
            className="btn btn-secondary"
            onClick={handleLogout}
            style={{ marginTop: '10px' }}
          >
            登出
          </button>
        </div>
      ) : (
        <div>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <button 
              className="btn"
              onClick={() => {
                setShowLoginForm(true);
                setShowCreateForm(false);
              }}
            >
              登录
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                setShowCreateForm(true);
                setShowLoginForm(false);
              }}
            >
              注册
            </button>
          </div>

          {showLoginForm && (
            <form onSubmit={handleLogin} style={{ marginTop: '20px' }}>
              <h3>用户登录</h3>
              <div className="form-group">
                <label>用户名:</label>
                <input
                  type="text"
                  value={loginData.username}
                  onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                  required
                  minLength="2"
                />
              </div>
              <div className="form-group">
                <label>密码:</label>
                <input
                  type="password"
                  value={loginData.password}
                  onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                  required
                  minLength="6"
                />
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button type="submit" className="btn">登录</button>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowLoginForm(false)}
                >
                  取消
                </button>
              </div>
            </form>
          )}

          {showCreateForm && (
            <form onSubmit={handleCreateUser} style={{ marginTop: '20px' }}>
              <h3>用户注册</h3>
              <div className="form-group">
                <label>用户名:</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  required
                  minLength="2"
                />
              </div>
              <div className="form-group">
                <label>邮箱:</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>密码:</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  required
                  minLength="6"
                />
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button type="submit" className="btn">注册</button>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setShowCreateForm(false)}
                >
                  取消
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
};

export default UserSelector;
