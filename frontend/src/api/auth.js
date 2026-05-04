import axios from 'axios'
import { useAuthStore } from '../store/auth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const authStore = useAuthStore()
      if (authStore.refreshToken) {
        try {
          const success = await authStore.refreshAccessToken()
          if (success) {
            originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
            return apiClient(originalRequest)
          }
        } catch (refreshError) {
          authStore.logout()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }
    }

    return Promise.reject(error)
  }
)

export default {
  async login(username, password) {
    const response = await apiClient.post('/auth/login', { username, password })
    return response.data
  },

  async register(username, email, password, fullName) {
    const response = await apiClient.post('/auth/register', {
      username,
      email,
      password,
      full_name: fullName
    })
    return response.data
  },

  async refreshToken(refreshToken) {
    const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },

  async getCurrentUser() {
    const response = await apiClient.get('/users/me')
    return response.data
  },

  async updateUser(data) {
    const response = await apiClient.patch('/users/me', data)
    return response.data
  }
}
