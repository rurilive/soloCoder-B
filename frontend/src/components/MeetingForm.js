import React, { useState, useEffect } from 'react';
import { userAPI } from '../services/api';

const MeetingForm = ({ onSubmit, initialData = null, onCancel, currentUser }) => {
  const [users, setUsers] = useState([]);
  const [formData, setFormData] = useState({
    title: initialData?.title || '',
    description: initialData?.description || '',
    start_time: initialData?.start_time 
      ? new Date(initialData.start_time).toISOString().slice(0, 16)
      : '',
    end_time: initialData?.end_time 
      ? new Date(initialData.end_time).toISOString().slice(0, 16)
      : '',
    location: initialData?.location || '',
    participant_ids: initialData?.participants?.map(p => p.user_id) || [],
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await userAPI.getAll();
      setUsers(response.data);
    } catch (err) {
      console.error('获取用户列表失败:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleParticipantChange = (e) => {
    const userId = parseInt(e.target.value);
    const isChecked = e.target.checked;
    
    setFormData(prev => ({
      ...prev,
      participant_ids: isChecked
        ? [...prev.participant_ids, userId]
        : prev.participant_ids.filter(id => id !== userId),
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...formData,
      start_time: new Date(formData.start_time).toISOString(),
      end_time: new Date(formData.end_time).toISOString(),
      organizer_id: currentUser.id,
    });
  };

  const otherUsers = users.filter(u => u.id !== currentUser?.id);

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>{initialData ? '编辑会议' : '创建会议'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>会议标题:</label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label>描述:</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows="3"
            />
          </div>
          <div className="form-group">
            <label>开始时间:</label>
            <input
              type="datetime-local"
              name="start_time"
              value={formData.start_time}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label>结束时间:</label>
            <input
              type="datetime-local"
              name="end_time"
              value={formData.end_time}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label>地点:</label>
            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              placeholder="例如：会议室A / Zoom链接"
            />
          </div>
          <div className="form-group">
            <label>邀请参与者:</label>
            <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #ddd', borderRadius: '5px', padding: '10px' }}>
              {otherUsers.length === 0 ? (
                <p style={{ color: '#888' }}>暂无其他用户可邀请</p>
              ) : (
                otherUsers.map(user => (
                  <div key={user.id} className="checkbox-group" style={{ margin: '5px 0' }}>
                    <input
                      type="checkbox"
                      id={`user-${user.id}`}
                      value={user.id}
                      checked={formData.participant_ids.includes(user.id)}
                      onChange={handleParticipantChange}
                    />
                    <label htmlFor={`user-${user.id}`}>
                      {user.username} ({user.email})
                    </label>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              取消
            </button>
            <button type="submit" className="btn">
              {initialData ? '更新' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MeetingForm;
