import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach Access Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('socialpilot_access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Token Refresh on 401
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/register')) {
        return Promise.reject(error);
      }

      const refreshToken = localStorage.getItem('socialpilot_refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('socialpilot_access_token');
        localStorage.removeItem('socialpilot_refresh_token');
        localStorage.removeItem('socialpilot_user');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken, user } = response.data;
        localStorage.setItem('socialpilot_access_token', access_token);
        if (newRefreshToken) {
          localStorage.setItem('socialpilot_refresh_token', newRefreshToken);
        }
        if (user) {
          localStorage.setItem('socialpilot_user', JSON.stringify(user));
        }

        api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem('socialpilot_access_token');
        localStorage.removeItem('socialpilot_refresh_token');
        localStorage.removeItem('socialpilot_user');
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Modular API Client Methods
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (email, password, full_name) => api.post('/auth/register', { email, password, full_name }),
  googleAuth: (credential) => api.post('/auth/google', { credential }),
  getMe: () => api.get('/auth/me'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
};

export const userAPI = {
  getProfile: () => api.get('/users/me'),
  updateProfile: (data) => api.patch('/users/me', data),
};

export const accountsAPI = {
  list: (params) => api.get('/accounts', { params }),
  get: (id) => api.get(`/accounts/${id}`),
  connect: (data) => api.post('/accounts', data),
  getStatus: (id) => api.get(`/accounts/${id}/status`),
  updatePermissions: (id, permissions) => api.patch(`/accounts/${id}/permissions`, { platform_permissions: permissions }),
  sync: (id) => api.post(`/accounts/${id}/sync`),
  disconnect: (id) => api.delete(`/accounts/${id}`),
};

export const oauthAPI = {
  getAuthorizationUrl: (provider, teamId) =>
    api.get(`/oauth/${provider}/authorize`, {
      params: teamId ? { team_id: teamId } : {},
    }),
};

export const postsAPI = {
  create: (data) => api.post('/posts', data),
  list: (params) => api.get('/posts', { params }),
  get: (id) => api.get(`/posts/${id}`),
  update: (id, data) => api.put(`/posts/${id}`, data),
  delete: (id) => api.delete(`/posts/${id}`),
  schedule: (id, scheduled_at) => api.post(`/posts/${id}/schedule`, { scheduled_at }),
  unschedule: (id) => api.post(`/posts/${id}/unschedule`),
  publish: (id) => api.post(`/posts/${id}/publish`),
  cancel: (id) => api.post(`/posts/${id}/cancel`),
  getStatus: (id) => api.get(`/posts/${id}/status`),
  submitForApproval: (id) => api.post(`/posts/${id}/submit-for-approval`),
  approve: (id) => api.post(`/posts/${id}/approve`),
  reject: (id, reason) => api.post(`/posts/${id}/reject`, { reason }),
};

export const mediaAPI = {
  upload: (formData) => api.post('/media', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  list: (params) => api.get('/media', { params }),
  get: (mediaId) => api.get(`/media/${mediaId}`),
  delete: (mediaId) => api.delete(`/media/${mediaId}`),
};

export const teamsAPI = {
  list: () => api.get('/teams'),
  create: (data) => api.post('/teams', data),
  get: (id) => api.get(`/teams/${id}`),
  update: (id, data) => api.put(`/teams/${id}`, data),
  delete: (id) => api.delete(`/teams/${id}`),
  listMembers: (id) => api.get(`/teams/${id}/members`),
  addMember: (id, data) => api.post(`/teams/${id}/members`, data),
  updateMemberRole: (teamId, userId, role) => api.put(`/teams/${teamId}/members/${userId}`, { role }),
  removeMember: (teamId, userId) => api.delete(`/teams/${teamId}/members/${userId}`),
  listInvitations: (teamId) => api.get(`/teams/${teamId}/invitations`),
  createInvitation: (teamId, data) => api.post(`/teams/${teamId}/invitations`, data),
  cancelInvitation: (teamId, invitationId) => api.post(`/teams/${teamId}/invitations/${invitationId}/cancel`),
  listActivity: (teamId, params) => api.get(`/teams/${teamId}/activity`, { params }),
};

export const invitationsAPI = {
  get: (token) => api.get(`/invitations/${token}`),
  accept: (token) => api.post(`/invitations/${token}/accept`),
  reject: (token) => api.post(`/invitations/${token}/reject`),
};

export const campaignsAPI = {
  list: (teamId, params) => api.get('/campaigns', { params: { team_id: teamId, ...params } }),
  get: (campaignId, teamId) => api.get(`/campaigns/${campaignId}`, { params: { team_id: teamId } }),
  create: (teamId, data) => api.post('/campaigns', data, { params: { team_id: teamId } }),
  update: (campaignId, teamId, data) => api.put(`/campaigns/${campaignId}`, data, { params: { team_id: teamId } }),
  delete: (campaignId, teamId) => api.delete(`/campaigns/${campaignId}`, { params: { team_id: teamId } }),
  getPosts: (campaignId, teamId, params) => api.get(`/campaigns/${campaignId}/posts`, { params: { team_id: teamId, ...params } }),
};

export const analyticsAPI = {
  getOverview: (teamId, days = 30) => api.get('/analytics/overview', { params: { team_id: teamId, days } }),
  getPostsTimeline: (teamId, days = 30) => api.get('/analytics/posts/timeline', { params: { team_id: teamId, days } }),
  getCampaignPerformance: (teamId) => api.get('/analytics/campaigns/performance', { params: { team_id: teamId } }),
};

export const notificationsAPI = {
  list: (params) => api.get('/notifications', { params }),
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markAsRead: (id) => api.patch(`/notifications/${id}/read`),
  markAllAsRead: () => api.patch('/notifications/read-all'),
};

export const reportsAPI = {
  downloadPDF: (teamId, days = 30) =>
    api.get('/reports/pdf', {
      params: { team_id: teamId, days },
      responseType: 'blob',
    }),
  downloadExcel: (teamId, days = 30) =>
    api.get('/reports/excel', {
      params: { team_id: teamId, days },
      responseType: 'blob',
    }),
};



