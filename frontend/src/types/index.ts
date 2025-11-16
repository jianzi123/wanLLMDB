// User types
export interface User {
  id: string
  username: string
  email: string
  fullName?: string
  avatarUrl?: string
  isActive: boolean
  createdAt: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: string
}

// Project types
export interface Project {
  id: string
  name: string
  slug: string
  description?: string
  visibility: 'public' | 'private'
  createdBy: string
  createdAt: string
  updatedAt: string
  runCount?: number
  lastActivity?: string
}

// Run types
export type RunState = 'running' | 'finished' | 'crashed' | 'killed'

export interface Run {
  id: string
  name?: string
  projectId: string
  userId: string
  state: RunState
  gitCommit?: string
  gitRemote?: string
  gitBranch?: string
  host?: string
  os?: string
  pythonVersion?: string
  startedAt: string
  finishedAt?: string
  heartbeatAt: string
  notes?: string
  tags: string[]
  config: Record<string, unknown>
  summary: Record<string, unknown>
}

// Metric types
export interface MetricValue {
  step: number
  value: number
  timestamp: string
}

export interface MetricData {
  [metricName: string]: MetricValue[]
}

// API response types
export interface ApiResponse<T> {
  data: T
  meta?: {
    timestamp: string
    version?: string
  }
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    pageSize: number
    totalPages: number
  }
  links?: {
    first?: string
    prev?: string
    next?: string
    last?: string
  }
}

export interface ApiError {
  code: string
  message: string
  details?: Array<{
    field: string
    message: string
  }>
}

// Form types
export interface LoginFormData {
  username: string
  password: string
}

export interface RegisterFormData {
  username: string
  email: string
  password: string
  fullName?: string
}

export interface ProjectFormData {
  name: string
  description?: string
  visibility: 'public' | 'private'
}
