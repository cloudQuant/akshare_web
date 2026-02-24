import request from '@/utils/request'

export interface DatabaseConfig {
  host: string
  port: number
  database: string
  user: string
  password?: string
}

export const settingsApi = {
  // Get main database config
  getDatabaseConfig(): Promise<any> {
    return request({
      url: '/settings/database',
      method: 'GET'
    })
  },

  // Get warehouse database config
  getWarehouseConfig(): Promise<any> {
    return request({
      url: '/settings/database/warehouse',
      method: 'GET'
    })
  },

  // Test database connection
  testConnection(config: DatabaseConfig): Promise<any> {
    return request({
      url: '/settings/database/test',
      method: 'POST',
      data: config
    })
  },

  // Test warehouse connection
  testWarehouseConnection(config: DatabaseConfig): Promise<any> {
    return request({
      url: '/settings/database/warehouse/test',
      method: 'POST',
      data: config
    })
  },

  // Update database config
  updateDatabaseConfig(config: DatabaseConfig): Promise<any> {
    return request({
      url: '/settings/database',
      method: 'PUT',
      data: config
    })
  }
}
