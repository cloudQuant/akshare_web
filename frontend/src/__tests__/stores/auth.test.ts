import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock the auth API
vi.mock('@/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    refreshToken: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  it('initializes with null values', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.refreshToken).toBeNull()
  })

  it('isAuthenticated returns false when no user/token', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
  })

  it('isAuthenticated returns true when user and token exist', () => {
    const store = useAuthStore()
    store.user = { id: 1, email: 'test@example.com', role: 'user', is_active: true, created_at: '', updated_at: '' } as any
    store.accessToken = 'token123'
    expect(store.isAuthenticated).toBe(true)
  })

  it('isAdmin returns false for regular user', () => {
    const store = useAuthStore()
    store.user = { id: 1, role: 'user' } as any
    expect(store.isAdmin).toBe(false)
  })

  it('isAdmin returns true for admin user', () => {
    const store = useAuthStore()
    store.user = { id: 1, role: 'admin' } as any
    expect(store.isAdmin).toBe(true)
  })

  it('login sets tokens and user', async () => {
    const { authApi } = await import('@/api/auth')
    const mockResponse = {
      access_token: 'access123',
      refresh_token: 'refresh123',
      user: { id: 1, email: 'test@example.com', role: 'user' },
    }
    vi.mocked(authApi.login).mockResolvedValue(mockResponse as any)

    const store = useAuthStore()
    await store.login({ email: 'test@example.com', password: 'pass' })

    expect(store.accessToken).toBe('access123')
    expect(store.refreshToken).toBe('refresh123')
    expect(store.user).toEqual(mockResponse.user)
    expect(localStorageMock.setItem).toHaveBeenCalled()
  })

  it('register sets tokens and user', async () => {
    const { authApi } = await import('@/api/auth')
    const mockResponse = {
      access_token: 'access456',
      refresh_token: 'refresh456',
      user: { id: 2, email: 'new@example.com', role: 'user' },
    }
    vi.mocked(authApi.register).mockResolvedValue(mockResponse as any)

    const store = useAuthStore()
    await store.register({ email: 'new@example.com', password: 'pass', password_confirm: 'pass' })

    expect(store.accessToken).toBe('access456')
    expect(store.user).toEqual(mockResponse.user)
  })

  it('logout clears state', () => {
    const store = useAuthStore()
    store.user = { id: 1 } as any
    store.accessToken = 'token'
    store.refreshToken = 'refresh'

    store.logout()

    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.refreshToken).toBeNull()
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_user')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_access_token')
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_refresh_token')
  })

  it('setUser updates user', () => {
    const store = useAuthStore()
    const user = { id: 1, email: 'test@example.com' } as any
    store.setUser(user)
    expect(store.user).toEqual(user)
  })

  it('persistAuth saves to localStorage', () => {
    const store = useAuthStore()
    store.user = { id: 1 } as any
    store.accessToken = 'access'
    store.refreshToken = 'refresh'

    store.persistAuth()

    expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_user', JSON.stringify({ id: 1 }))
    expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_access_token', 'access')
    expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_refresh_token', 'refresh')
  })

  it('restoreAuth loads from localStorage', () => {
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === 'auth_user') return JSON.stringify({ id: 1, email: 'test@example.com' })
      if (key === 'auth_access_token') return 'saved_access'
      if (key === 'auth_refresh_token') return 'saved_refresh'
      return null
    })

    const store = useAuthStore()
    store.restoreAuth()

    expect(store.user).toEqual({ id: 1, email: 'test@example.com' })
    expect(store.accessToken).toBe('saved_access')
    expect(store.refreshToken).toBe('saved_refresh')
  })

  it('restoreAuth handles invalid JSON gracefully', () => {
    localStorageMock.getItem.mockImplementation((key: string) => {
      if (key === 'auth_user') return 'invalid-json'
      return null
    })

    const store = useAuthStore()
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    store.restoreAuth()
    consoleSpy.mockRestore()

    expect(store.user).toBeNull()
  })

  it('refreshAccessToken throws when no refresh token', async () => {
    const store = useAuthStore()
    store.refreshToken = null

    await expect(store.refreshAccessToken()).rejects.toThrow('No refresh token available')
  })

  it('refreshAccessToken updates tokens', async () => {
    const { authApi } = await import('@/api/auth')
    vi.mocked(authApi.refreshToken).mockResolvedValue({
      access_token: 'new_access',
      refresh_token: 'new_refresh',
    } as any)

    const store = useAuthStore()
    store.refreshToken = 'old_refresh'

    await store.refreshAccessToken()

    expect(store.accessToken).toBe('new_access')
    expect(store.refreshToken).toBe('new_refresh')
  })
})
