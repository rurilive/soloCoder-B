import React, { useState } from 'react';
import UserSelector from './components/UserSelector';
import EventList from './components/EventList';
import MeetingList from './components/MeetingList';

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [activeTab, setActiveTab] = useState('events');  // events, meetings, public

  return (
    <div className="container">
      <div className="header">
        <h1>📅 日程共享与会议安排</h1>
        <p>轻松管理您的日程，与他人共享，高效安排会议</p>
        
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
      </div>

      <UserSelector 
        currentUser={currentUser} 
        onUserChange={setCurrentUser} 
      />

      {activeTab === 'events' && (
        <EventList currentUser={currentUser} filterPublic={false} />
      )}

      {activeTab === 'public' && (
        <EventList currentUser={currentUser} filterPublic={true} />
      )}

      {activeTab === 'meetings' && (
        <MeetingList currentUser={currentUser} />
      )}
    </div>
  );
}

export default App;
