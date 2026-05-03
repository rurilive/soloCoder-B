import React, { useState, useEffect } from 'react';
import { meetingAPI } from '../services/api';
import MeetingForm from './MeetingForm';

const MeetingList = ({ currentUser }) => {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingMeeting, setEditingMeeting] = useState(null);
  const [activeTab, setActiveTab] = useState('all');  // all, organized, participating

  useEffect(() => {
    if (currentUser) {
      fetchMeetings();
    }
  }, [currentUser, activeTab]);

  const fetchMeetings = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (activeTab === 'organized') {
        params.organizer_id = currentUser.id;
      } else if (activeTab === 'participating') {
        params.participant_id = currentUser.id;
      }
      
      const response = await meetingAPI.getAll(params);
      setMeetings(response.data);
    } catch (err) {
      setError('获取会议列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMeeting = async (meetingData) => {
    try {
      await meetingAPI.create(meetingData);
      setShowForm(false);
      setSuccess('会议创建成功！');
      setTimeout(() => setSuccess(''), 3000);
      fetchMeetings();
    } catch (err) {
      setError(err.response?.data?.detail || '创建会议失败');
    }
  };

  const handleUpdateMeeting = async (meetingData) => {
    try {
      await meetingAPI.update(editingMeeting.id, meetingData);
      setEditingMeeting(null);
      setSuccess('会议更新成功！');
      setTimeout(() => setSuccess(''), 3000);
      fetchMeetings();
    } catch (err) {
      setError(err.response?.data?.detail || '更新会议失败');
    }
  };

  const handleDeleteMeeting = async (meetingId) => {
    if (window.confirm('确定要删除这个会议吗？')) {
      try {
        await meetingAPI.delete(meetingId);
        setSuccess('会议删除成功！');
        setTimeout(() => setSuccess(''), 3000);
        fetchMeetings();
      } catch (err) {
        setError('删除会议失败');
      }
    }
  };

  const handleUpdateStatus = async (meetingId, status) => {
    try {
      await meetingAPI.updateParticipantStatus(meetingId, currentUser.id, status);
      setSuccess(`状态已更新为: ${status === 'accepted' ? '已接受' : status === 'declined' ? '已拒绝' : '待定'}`);
      setTimeout(() => setSuccess(''), 3000);
      fetchMeetings();
    } catch (err) {
      setError('更新状态失败');
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getParticipantStatus = (meeting) => {
    if (!meeting.participants) return null;
    return meeting.participants.find(p => p.user_id === currentUser.id);
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  if (!currentUser) {
    return (
      <div className="card">
        <h2>我的会议</h2>
        <div className="empty-state">请先选择用户以查看会议</div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2>我的会议</h2>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <button 
        className="btn" 
        onClick={() => setShowForm(true)}
        style={{ marginBottom: '20px' }}
      >
        + 创建新会议
      </button>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          全部会议
        </button>
        <button 
          className={`tab ${activeTab === 'organized' ? 'active' : ''}`}
          onClick={() => setActiveTab('organized')}
        >
          我组织的
        </button>
        <button 
          className={`tab ${activeTab === 'participating' ? 'active' : ''}`}
          onClick={() => setActiveTab('participating')}
        >
          我参与的
        </button>
      </div>

      {meetings.length === 0 ? (
        <div className="empty-state">暂无会议</div>
      ) : (
        <div className="meeting-list">
          {meetings.map(meeting => {
            const myStatus = getParticipantStatus(meeting);
            const isOrganizer = meeting.organizer_id === currentUser.id;

            return (
              <div key={meeting.id} className="meeting-item">
                <h3>{meeting.title}</h3>
                {meeting.description && <p>{meeting.description}</p>}
                <div className="meeting-meta">
                  <span>开始: {formatDateTime(meeting.start_time)}</span>
                  <span>结束: {formatDateTime(meeting.end_time)}</span>
                </div>
                {meeting.location && (
                  <div className="meeting-meta">
                    <span>📍 地点: {meeting.location}</span>
                  </div>
                )}
                {meeting.organizer && (
                  <div className="meeting-meta">
                    <span>组织者: {meeting.organizer.username}</span>
                  </div>
                )}
                
                {meeting.participants && meeting.participants.length > 0 && (
                  <div className="participants">
                    <h4>参与者 ({meeting.participants.length}人):</h4>
                    {meeting.participants.map(participant => (
                      <span 
                        key={participant.id} 
                        className={`participant-tag ${participant.status}`}
                      >
                        {participant.user?.username || `用户${participant.user_id}`}
                        ({participant.status === 'accepted' ? '已接受' : 
                          participant.status === 'declined' ? '已拒绝' : '待定'})
                      </span>
                    ))}
                  </div>
                )}

                <div className="actions">
                  {isOrganizer ? (
                    <>
                      <button 
                        className="btn btn-secondary btn-small"
                        onClick={() => setEditingMeeting(meeting)}
                      >
                        编辑
                      </button>
                      <button 
                        className="btn btn-danger btn-small"
                        onClick={() => handleDeleteMeeting(meeting.id)}
                      >
                        删除
                      </button>
                    </>
                  ) : myStatus && (
                    <div style={{ display: 'flex', gap: '5px' }}>
                      <button 
                        className={`btn btn-small ${myStatus.status === 'accepted' ? '' : 'btn-secondary'}`}
                        onClick={() => handleUpdateStatus(meeting.id, 'accepted')}
                      >
                        接受
                      </button>
                      <button 
                        className={`btn btn-small ${myStatus.status === 'declined' ? 'btn-danger' : 'btn-secondary'}`}
                        onClick={() => handleUpdateStatus(meeting.id, 'declined')}
                      >
                        拒绝
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <MeetingForm
          onSubmit={handleCreateMeeting}
          onCancel={() => setShowForm(false)}
          currentUser={currentUser}
        />
      )}

      {editingMeeting && (
        <MeetingForm
          initialData={editingMeeting}
          onSubmit={handleUpdateMeeting}
          onCancel={() => setEditingMeeting(null)}
          currentUser={currentUser}
        />
      )}
    </div>
  );
};

export default MeetingList;
