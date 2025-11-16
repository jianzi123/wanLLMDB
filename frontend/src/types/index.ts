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

export interface Metric {
  time: string
  run_id: string
  metric_name: string
  step?: number
  value: number
  metadata?: Record<string, any>
}

export interface MetricStats {
  metric_name: string
  count: number
  min_value: number
  max_value: number
  avg_value: number
  std_dev?: number
  first_time: string
  last_time: string
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

// Artifact types
export type ArtifactType = 'model' | 'dataset' | 'file' | 'code'

export interface Artifact {
  id: string
  name: string
  type: ArtifactType
  description?: string
  projectId: string
  createdBy: string
  metadata?: Record<string, unknown>
  tags?: string[]
  versionCount: number
  latestVersion?: string
  createdAt: string
  updatedAt: string
}

export interface ArtifactVersion {
  id: string
  artifactId: string
  version: string
  description?: string
  notes?: string
  fileCount: number
  totalSize: number
  storagePath: string
  metadata?: Record<string, unknown>
  digest?: string
  runId?: string
  isFinalized: boolean
  createdBy: string
  createdAt: string
  finalizedAt?: string
}

export interface ArtifactFile {
  id: string
  versionId: string
  path: string
  name: string
  size: number
  mimeType?: string
  storageKey: string
  md5Hash?: string
  sha256Hash?: string
  createdAt: string
}

export interface ArtifactVersionWithFiles extends ArtifactVersion {
  files: ArtifactFile[]
}

export interface FileUploadRequest {
  path: string
}

export interface FileUploadResponse {
  uploadUrl: string
  storageKey: string
  expiresIn: number
}

export interface FileDownloadResponse {
  downloadUrl: string
  fileName: string
  size: number
  mimeType?: string
  expiresIn: number
}

export interface ArtifactList {
  items: Artifact[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface ArtifactVersionList {
  items: ArtifactVersion[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface ArtifactFormData {
  name: string
  type: ArtifactType
  description?: string
  projectId: string
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface ArtifactVersionFormData {
  artifactId: string
  version?: string
  description?: string
  notes?: string
  runId?: string
  metadata?: Record<string, unknown>
}
