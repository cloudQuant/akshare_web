import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginRequest, RegisterRequest } from '@/types'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore(
  'auth',
  () => {
    // State
    const user = ref<User | null>(null)
    const accessToken = ref<string | null>(null)
    const refreshToken = ref<string | null>(null)

    // Computed
    const isAuthenticated = computed(() => !!user.value && !!accessToken.value)
    const isAdmin = computed(() => user.value?.role?.toLowerCase() === 'admin')

    // Actions
    async function login(credentials: LoginRequest): Promise<void> {
      const response = await authApi.login(credentials)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      user.value = response.user
      persistAuth()
    }

    async function register(data: RegisterRequest): Promise<void> {
      const response = await authApi.register(data)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      // Register API may return partial user info (user_id, email) instead of full User object
      if (response.user) {
        user.value = response.user
      } else {
        // Fetch full user profile with the new token
        const me = await authApi.getCurrentUser()
        user.value = me as unknown as User
      }
      persistAuth()
    }

    async function refreshAccessToken(): Promise<void> {
      if (!refreshToken.value) {
        throw new Error('No refresh token available')
      }
      const response = await authApi.refreshToken(refreshToken.value)
      accessToken.value = response.access_token
      // Update refresh token if new one is provided
      if (response.refresh_token) {
        refreshToken.value = response.refresh_token
      }
      persistAuth()
    }

    function logout(): void {
      user.value = null
      accessToken.value = null
      refreshToken.value = null
      clearAuth()
    }

    function setUser(userData: User): void {
      user.value = userData
    }

    // Persist auth state to localStorage
    function persistAuth(): void {
      localStorage.setItem('auth_user', JSON.stringify(user.value))
      localStorage.setItem('auth_access_token', accessToken.value || '')
      localStorage.setItem('auth_refresh_token', refreshToken.value || '')
    }

    // Clear auth state from localStorage
    function clearAuth(): void {
      localStorage.removeItem('auth_user')
      localStorage.removeItem('auth_access_token')
      localStorage.removeItem('auth_refresh_token')
    }

    // Restore auth state from localStorage
    function restoreAuth(): void {
      const savedUser = localStorage.getItem('auth_user')
      const savedAccessToken = localStorage.getItem('auth_access_token')
      const savedRefreshToken = localStorage.getItem('auth_refresh_token')

      if (savedUser) {
        try {
          user.value = JSON.parse(savedUser)
        } catch (e) {
          console.error('Failed to parse saved user', e)
        }
      }
      accessToken.value = savedAccessToken
      refreshToken.value = savedRefreshToken
    }

    return {
      user,
      accessToken,
      refreshToken,
      isAuthenticated,
      isAdmin,
      login,
      register,
      refreshAccessToken,
      logout,
      setUser,
      persistAuth,
      clearAuth,
      restoreAuth,
    }
  },
)

