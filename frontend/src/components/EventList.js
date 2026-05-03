import React, { useState, useEffect } from 'react';
import { eventAPI } from '../services/api';
import EventForm from './EventForm';

const EventList = ({ currentUser, filterPublic = false }) => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (currentUser || filterPublic) {
      fetchEvents();
    }
  }, [currentUser, filterPublic]);

  const fetchEvents = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (filterPublic) {
        params.is_public = true;
      } else if (currentUser) {
        params.user_id = currentUser.id;
      }
      
      const response = await eventAPI.getAll(params);
      setEvents(response.data);
    } catch (err) {
      setError('获取日程列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEvent = async (eventData) => {
    try {
      await eventAPI.create({
        ...eventData,
        owner_id: currentUser.id,
      });
      setShowForm(false);
      setSuccess('日程创建成功！');
      setTimeout(() => setSuccess(''), 3000);
      fetchEvents();
    } catch (err) {
      setError(err.response?.data?.detail || '创建日程失败');
    }
  };

  const handleUpdateEvent = async (eventData) => {
    try {
      await eventAPI.update(editingEvent.id, {
        ...eventData,
        owner_id: currentUser.id,
      });
      setEditingEvent(null);
      setSuccess('日程更新成功！');
      setTimeout(() => setSuccess(''), 3000);
      fetchEvents();
    } catch (err) {
      setError(err.response?.data?.detail || '更新日程失败');
    }
  };

  const handleDeleteEvent = async (eventId) => {
    if (window.confirm('确定要删除这个日程吗？')) {
      try {
        await eventAPI.delete(eventId);
        setSuccess('日程删除成功！');
        setTimeout(() => setSuccess(''), 3000);
        fetchEvents();
      } catch (err) {
        setError('删除日程失败');
      }
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="card">
      <h2>{filterPublic ? '公开日程' : '我的日程'}</h2>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {!filterPublic && currentUser && (
        <button 
          className="btn" 
          onClick={() => setShowForm(true)}
          style={{ marginBottom: '20px' }}
        >
          + 创建新日程
        </button>
      )}

      {events.length === 0 ? (
        <div className="empty-state">
          {filterPublic ? '暂无公开日程' : '暂无日程，点击上方按钮创建第一个日程'}
        </div>
      ) : (
        <div className="event-list">
          {events.map(event => (
            <div 
              key={event.id} 
              className={`event-item ${event.is_public ? 'public' : ''}`}
            >
              <h3>{event.title}</h3>
              {event.description && <p>{event.description}</p>}
              <div className="event-meta">
                <span>开始: {formatDateTime(event.start_time)}</span>
                <span>结束: {formatDateTime(event.end_time)}</span>
                {event.is_public && <span>📢 公开</span>}
              </div>
              {event.owner && (
                <div className="event-meta">
                  <span>创建者: {event.owner.username}</span>
                </div>
              )}
              {!filterPublic && currentUser && event.owner_id === currentUser.id && (
                <div className="actions">
                  <button 
                    className="btn btn-secondary btn-small"
                    onClick={() => setEditingEvent(event)}
                  >
                    编辑
                  </button>
                  <button 
                    className="btn btn-danger btn-small"
                    onClick={() => handleDeleteEvent(event.id)}
                  >
                    删除
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <EventForm
          onSubmit={handleCreateEvent}
          onCancel={() => setShowForm(false)}
        />
      )}

      {editingEvent && (
        <EventForm
          initialData={editingEvent}
          onSubmit={handleUpdateEvent}
          onCancel={() => setEditingEvent(null)}
        />
      )}
    </div>
  );
};

export default EventList;
