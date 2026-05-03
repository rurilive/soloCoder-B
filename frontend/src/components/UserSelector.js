import React, { useState, useEffect } from 'react';
import { userAPI } from '../services/api';

const UserSelector = ({ currentUser, onUserChange }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchUsers();
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
      setNewUser({ username: '', email: '' });
      setShowCreateForm(false);
      setSuccess('用户创建成功！');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || '创建用户失败');
    }
  };

  return (
    <div className="card">
      <h2>用户选择</h2>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {currentUser && (
        <div className="current-user">
          <h3>当前用户: {currentUser.username}</h3>
          <p>邮箱: {currentUser.email}</p>
        </div>
      )}

      <div className="form-group">
        <label>选择用户:</label>
        <select
          value={currentUser?.id || ''}
          onChange={(e) => {
            const selected = users.find(u => u.id === parseInt(e.target.value));
            onUserChange(selected);
          }}
        >
          <option value="">请选择用户</option>
          {users.map(user => (
            <option key={user.id} value={user.id}>
              {user.username} ({user.email})
            </option>
          ))}
        </select>
      </div>

      <button 
        className="btn btn-secondary"
        onClick={() => setShowCreateForm(!showCreateForm)}
      >
        {showCreateForm ? '取消' : '创建新用户'}
      </button>

      {showCreateForm && (
        <form onSubmit={handleCreateUser} style={{ marginTop: '20px' }}>
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
          <button type="submit" className="btn">创建用户</button>
        </form>
      )}
    </div>
  );
};

export default UserSelector;
