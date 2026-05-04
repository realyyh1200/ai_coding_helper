import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function login(username, password) {
    try {
      const response = await api.login(username, password)
      setTokens(response.access_token, response.refresh_token)
      await fetchUser()
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function register(username, email, password, fullName) {
    try {
      await api.register(username, email, password, fullName)
      return await login(username, password)
    } catch (error) {
      console.error('Registration failed:', error)
      return false
    }
  }

  async function fetchUser() {
    try {
      user.value = await api.getCurrentUser()
    } catch (error) {
      console.error('Failed to fetch user:', error)
      logout()
    }
  }

  async function refreshAccessToken() {
    try {
      const response = await api.refreshToken(refreshToken.value)
      setTokens(response.access_token, response.refresh_token)
      return true
    } catch (error) {
      console.error('Token refresh failed:', error)
      logout()
      return false
    }
  }

  function logout() {
    clearTokens()
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    login,
    register,
    fetchUser,
    refreshAccessToken,
    logout,
    setTokens
  }
})
