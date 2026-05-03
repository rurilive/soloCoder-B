import React, { useState, useEffect } from 'react';
import UserSelector from './components/UserSelector';
import EventList from './components/EventList';
import MeetingList from './components/MeetingList';
import { getAuthToken, userAPI } from './services/api';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [activeTab, setActiveTab] = useState('events');  // events, meetings, public
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      checkAuthStatus();
    }
  }, []);

  const checkAuthStatus = async () => {
    setLoading(true);
    try {
      const response = await userAPI.getAll();
      setIsAuthenticated(true);
    } catch (err) {
      setIsAuthenticated(false);
      setError('会话已过期，请重新登录');
    } finally {
      setLoading(false);
    }
  };

  const handleAuthStatusChange = (status) => {
    setIsAuthenticated(status);
    if (!status) {
      setCurrentUser(null);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">加载中...</div>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <h1>📅 日程共享与会议安排</h1>
        <p>轻松管理您的日程，与他人共享，高效安排会议</p>
        
        {isAuthenticated && (
          <div className="nav">
            <button 
              className={activeTab === 'events' ? 'active' : ''}
              onClick={() => setActiveTab('events')}
            >
              我的日程
            </button>
            <button 
              className={activeTab === 'public' ? 'active' : ''}
              onClick={() => setActiveTab('public')}
            >
              公开日程
            </button>
            <button 
              className={activeTab === 'meetings' ? 'active' : ''}
              onClick={() => setActiveTab('meetings')}
            >
              我的会议
            </button>
          </div>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      <UserSelector 
        currentUser={currentUser} 
        onUserChange={setCurrentUser}
        onAuthStatusChange={handleAuthStatusChange}
      />

      {!isAuthenticated ? (
        <div className="card">
          <h2>欢迎使用</h2>
          <div className="empty-state">
            请先登录或注册以使用日程和会议管理功能
          </div>
        </div>
      ) : (
        <>
          {activeTab === 'events' && (
            <EventList currentUser={currentUser} filterPublic={false} />
          )}

          {activeTab === 'public' && (
            <EventList currentUser={currentUser} filterPublic={true} />
          )}

          {activeTab === 'meetings' && (
            <MeetingList currentUser={currentUser} />
          )}
        </>
      )}
    </div>
  );
}

export default App;
