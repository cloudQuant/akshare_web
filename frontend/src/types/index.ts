// API Response wrapper
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data: T
}

// Pagination
export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// User
export interface User {
  id: number
  email: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
  updated_at: string
}

// Auth
export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  password_confirm: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user: User
}

// Data Script / Interface
export interface DataScript {
  id: number
  script_id: string
  script_name: string
  category: string
  sub_category: string | null
  frequency: string | null
  description: string | null
  source: string
  target_table: string | null
  module_path: string | null
  function_name: string | null
  parameters?: Parameter[] | Record<string, any> | null
  estimated_duration: number
  timeout: number
  is_active: boolean
  is_custom: boolean
  created_at: string
  updated_at: string
}

export interface Parameter {
  name: string
  type: string
  required: boolean
  default_value?: any
  description: string
}

// Task
export interface Task {
  id: number
  name: string
  description: string | null
  user_id: number
  script_id: string
  script_name: string | null
  schedule_type: string
  schedule_expression: string
  parameters: Record<string, any>
  is_active: boolean
  retry_on_failure: boolean
  max_retries: number
  timeout: number
  last_execution_at: string | null
  next_execution_at: string | null
  created_at: string
  updated_at: string
}

// Execution
export interface Execution {
  id: number
  task_id?: number
  script_id: number
  status: 'pending' | 'running' | 'success' | 'failed'
  start_time: string
  end_time?: string
  duration?: number
  rows_processed?: number
  error_message?: string
  retry_count: number
  created_at: string
}

// Data Table
export interface DataTable {
  id: number
  table_name: string
  table_comment: string | null
  category: string | null
  script_id: string | null
  row_count: number
  last_update_time: string | null
  last_update_status: string | null
  created_at: string
  updated_at: string
}

export interface TableColumn {
  name: string
  type: string
  nullable: boolean
  key: string | null
  default: string | null
}

export interface TableSchema {
  table_name: string
  columns: TableColumn[]
  row_count: number
  last_update_time: string | null
}

// Stats
export interface ExecutionStats {
  total_count: number
  success_count: number
  failed_count: number
  success_rate: number
  avg_duration: number
  today_executions: number
}
