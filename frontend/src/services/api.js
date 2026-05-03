import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const userAPI = {
  create: (userData) => api.post('/users/', userData),
  getAll: () => api.get('/users/'),
  getById: (id) => api.get(`/users/${id}`),
};

export const eventAPI = {
  create: (eventData) => api.post('/events/', eventData),
  getAll: (params = {}) => api.get('/events/', { params }),
  getById: (id) => api.get(`/events/${id}`),
  update: (id, eventData) => api.put(`/events/${id}`, eventData),
  delete: (id) => api.delete(`/events/${id}`),
};

export const meetingAPI = {
  create: (meetingData) => api.post('/meetings/', meetingData),
  getAll: (params = {}) => api.get('/meetings/', { params }),
  getById: (id) => api.get(`/meetings/${id}`),
  update: (id, meetingData) => api.put(`/meetings/${id}`, meetingData),
  delete: (id) => api.delete(`/meetings/${id}`),
  addParticipant: (meetingId, userId) => 
    api.post(`/meetings/${meetingId}/participants/${userId}`),
  updateParticipantStatus: (meetingId, userId, status) => 
    api.put(`/meetings/${meetingId}/participants/${userId}/status?status=${status}`),
};

export default api;
