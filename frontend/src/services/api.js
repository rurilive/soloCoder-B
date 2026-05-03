import axios from 'axios';

const API_BASE_URL = '/api';

let authToken = null;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    localStorage.setItem('authToken', token);
  } else {
    localStorage.removeItem('authToken');
  }
};

export const getAuthToken = () => {
  if (!authToken) {
    authToken = localStorage.getItem('authToken');
  }
  return authToken;
};

export const userAPI = {
  create: (userData) => api.post('/users/', userData),
  login: (credentials) => api.post('/users/login', credentials),
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
