import React, { useState, useEffect } from 'react';
import { userAPI, setAuthToken, getAuthToken } from '../services/api';

const validatePasswordComplexity = (password) => {
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSymbol = /[!@#$%^&*(),.?":{}|<>]/.test(password);
  
  const categories = [hasUpper, hasLower, hasDigit, hasSymbol].filter(Boolean).length;
  
  return {
    isValid: categories >= 2,
    categories: { hasUpper, hasLower, hasDigit, hasSymbol },
    categoriesCount: categories
  };
};

const formatErrorDetail = (detail) => {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map(err => {
      if (err.msg) {
        const field = err.loc && err.loc.length > 0 ? err.loc[err.loc.length - 1] : '';
        return field ? `${field}: ${err.msg}` : err.msg;
      }
      return String(err);
    }).join('; ');
  }
  return String(detail);
};

const UserSelector = ({ currentUser, onUserChange, onAuthStatusChange }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '' });
  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passwordValidation, setPasswordValidation] = useState({
    isValid: true,
    categories: { hasUpper: false, hasLower: false, hasDigit: false, hasSymbol: false },
    categoriesCount: 0
  });

  const handlePasswordChange = (e) => {
    const password = e.target.value;
    setNewUser({ ...newUser, password: password });
    setPasswordValidation(validatePasswordComplexity(password));
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newUser.password.length > 0 && !passwordValidation.isValid) {
      setError('密码必须包含至少两类字符：大写字母、小写字母、数字、符号');
      return;
    }

    try {
      const response = await userAPI.create(newUser);
      const { access_token } = response.data;
      setAuthToken(access_token);
      
      const usersResponse = await userAPI.getAll();
      setUsers(usersResponse.data);
      
      const currentUserData = usersResponse.data.find(
        u => u.username === newUser.username
      );
      
      if (currentUserData) {
        onUserChange(currentUserData);
        onAuthStatusChange(true);
      }
      
      setNewUser({ username: '', email: '', password: '' });
      setShowCreateForm(false);
      setSuccess('注册并登录成功！');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(formatErrorDetail(err.response?.data?.detail) || '创建用户失败');
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
      setError(formatErrorDetail(err.response?.data?.detail) || '登录失败');
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
                <label>邮箱 (可选):</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  placeholder="可选"
                />
              </div>
              <div className="form-group">
                <label>密码:</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={handlePasswordChange}
                  required
                  minLength="6"
                  style={{
                    borderColor: newUser.password.length > 0 && !passwordValidation.isValid ? '#dc3545' : undefined
                  }}
                />
                <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
                  <p style={{ margin: '0 0 4px 0' }}>密码需要包含至少两类字符：</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={{ 
                      color: passwordValidation.categories.hasUpper ? '#28a745' : '#6c757d',
                      fontWeight: passwordValidation.categories.hasUpper ? 'bold' : 'normal'
                    }}>
                      {passwordValidation.categories.hasUpper ? '✓' : '○'} 大写字母
                    </span>
                    <span style={{ 
                      color: passwordValidation.categories.hasLower ? '#28a745' : '#6c757d',
                      fontWeight: passwordValidation.categories.hasLower ? 'bold' : 'normal'
                    }}>
                      {passwordValidation.categories.hasLower ? '✓' : '○'} 小写字母
                    </span>
                    <span style={{ 
                      color: passwordValidation.categories.hasDigit ? '#28a745' : '#6c757d',
                      fontWeight: passwordValidation.categories.hasDigit ? 'bold' : 'normal'
                    }}>
                      {passwordValidation.categories.hasDigit ? '✓' : '○'} 数字
                    </span>
                    <span style={{ 
                      color: passwordValidation.categories.hasSymbol ? '#28a745' : '#6c757d',
                      fontWeight: passwordValidation.categories.hasSymbol ? 'bold' : 'normal'
                    }}>
                      {passwordValidation.categories.hasSymbol ? '✓' : '○'} 符号
                    </span>
                  </div>
                  {newUser.password.length > 0 && (
                    <p style={{ 
                      margin: '8px 0 0 0',
                      color: passwordValidation.isValid ? '#28a745' : '#dc3545',
                      fontWeight: 'bold'
                    }}>
                      {passwordValidation.isValid 
                        ? `✓ 密码强度符合要求 (已包含 ${passwordValidation.categoriesCount} 类字符)`
                        : `✗ 密码强度不足 (当前仅包含 ${passwordValidation.categoriesCount} 类字符，需要至少 2 类)`
                      }
                    </p>
                  )}
                </div>
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
