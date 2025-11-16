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

// Sweep types
export type SweepMethod = 'random' | 'grid' | 'bayes'
export type SweepState = 'pending' | 'running' | 'paused' | 'finished' | 'failed' | 'canceled'
export type MetricGoal = 'minimize' | 'maximize'

export interface ParameterDistribution {
  // For categorical parameters
  values?: any[]

  // For continuous parameters
  distribution?: 'uniform' | 'log_uniform' | 'int_uniform' | 'normal'
  min?: number
  max?: number

  // For normal distribution
  mu?: number
  sigma?: number

  // For quantization
  q?: number
}

export interface SweepConfig {
  method: SweepMethod
  metric: {
    name: string
    goal: MetricGoal
  }
  parameters: Record<string, ParameterDistribution>
  early_terminate?: Record<string, any>
  run_cap?: number
}

export interface Sweep {
  id: string
  name: string
  description?: string
  projectId: string
  createdBy: string
  method: SweepMethod
  metricName: string
  metricGoal: MetricGoal
  config: Record<string, ParameterDistribution>
  earlyTerminate?: Record<string, any>
  state: SweepState
  runCount: number
  runCap?: number
  bestRunId?: string
  bestValue?: number
  optunaConfig?: Record<string, any>
  createdAt: string
  updatedAt: string
  startedAt?: string
  finishedAt?: string
}

export interface SweepRun {
  id: string
  sweepId: string
  runId: string
  trialNumber?: number
  trialState?: string
  suggestedParams?: Record<string, any>
  metricValue?: number
  isBest: boolean
  createdAt: string
  evaluatedAt?: string
}

export interface SweepStats {
  sweepId: string
  totalRuns: number
  completedRuns: number
  runningRuns: number
  failedRuns: number
  bestValue?: number
  bestRunId?: string
  bestParams?: Record<string, any>
  parameterImportance?: Record<string, number>
}

export interface SweepWithStats extends Sweep {
  stats?: SweepStats
}

export interface SweepRunDetail extends SweepRun {
  run?: Run
}

export interface ParallelCoordinatesData {
  sweepId: string
  dimensions: string[]
  data: Array<Record<string, any>>
  bestIndex?: number
}

export interface SweepList {
  items: Sweep[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface SweepFormData {
  name: string
  description?: string
  projectId: string
  method: SweepMethod
  metricName: string
  metricGoal: MetricGoal
  config: Record<string, ParameterDistribution>
  earlyTerminate?: Record<string, any>
  runCap?: number
}

export interface SweepSuggestResponse {
  suggestedParams: Record<string, any>
  trialNumber?: number
}
