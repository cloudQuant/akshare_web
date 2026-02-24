import request from '@/utils/request'
import type {
  ApiResponse,
  User,
  PaginationParams,
  PaginatedResponse,
} from '@/types'

export const usersApi = {
  // Get user list (admin only)
  list(params?: PaginationParams & { search?: string }): Promise<PaginatedResponse<User>> {
    return request({
      url: '/users/',
      method: 'GET',
      params,
    })
  },

  // Get user detail
  getDetail(userId: number): Promise<User> {
    return request({
      url: `/users/${userId}`,
      method: 'GET',
    })
  },

  // Update user role (admin only)
  updateRole(userId: number, role: 'Admin' | 'User'): Promise<void> {
    return request({
      url: `/users/${userId}/role`,
      method: 'PUT',
      data: { role },
    })
  },

  // Delete user (admin only)
  delete(userId: number): Promise<void> {
    return request({
      url: `/users/${userId}`,
      method: 'DELETE',
    })
  },
}
