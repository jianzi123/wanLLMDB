import { api } from './api'

export enum ModelStage {
  NONE = 'none',
  STAGING = 'staging',
  PRODUCTION = 'production',
  ARCHIVED = 'archived',
}

export interface RegisteredModel {
  id: string
  name: string
  description?: string
  tags: string[]
  projectId: string
  createdBy: string
  createdAt: string
  updatedAt: string
}

export interface RegisteredModelWithVersions extends RegisteredModel {
  versions: ModelVersion[]
}

export interface RegisteredModelList {
  items: RegisteredModel[]
  total: number
  skip: number
  limit: number
}

export interface ModelVersion {
  id: string
  modelId: string
  version: string
  description?: string
  stage: ModelStage
  runId?: string
  artifactVersionId?: string
  metrics: Record<string, number>
  tags: string[]
  metadata: Record<string, any>
  approvedBy?: string
  approvedAt?: string
  createdAt: string
  updatedAt: string
}

export interface ModelVersionList {
  items: ModelVersion[]
  total: number
  skip: number
  limit: number
}

export interface StageTransitionRequest {
  stage: ModelStage
  comment?: string
}

export interface ModelVersionTransition {
  id: string
  modelVersionId: string
  fromStage: ModelStage
  toStage: ModelStage
  comment?: string
  transitionedBy: string
  transitionedAt: string
}

export interface ModelVersionTransitionList {
  items: ModelVersionTransition[]
  total: number
}

export interface ModelRegistrySummary {
  totalModels: number
  totalVersions: number
  byStage: Record<string, number>
}

export interface RegisteredModelCreate {
  name: string
  description?: string
  tags?: string[]
  projectId: string
}

export interface RegisteredModelUpdate {
  description?: string
  tags?: string[]
}

export interface ModelVersionCreate {
  version: string
  description?: string
  stage?: ModelStage
  runId?: string
  artifactVersionId?: string
  metrics?: Record<string, number>
  tags?: string[]
  metadata?: Record<string, any>
}

export interface ModelVersionUpdate {
  description?: string
  tags?: string[]
  metadata?: Record<string, any>
}

export const modelRegistryApi = api.injectEndpoints({
  endpoints: builder => ({
    // Registered Model endpoints
    createModel: builder.mutation<RegisteredModel, RegisteredModelCreate>({
      query: data => ({
        url: '/registry/models',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'RegisteredModel', id: 'LIST' }],
    }),

    listModels: builder.query<RegisteredModelList, {
      projectId?: string
      search?: string
      skip?: number
      limit?: number
    }>({
      query: ({ projectId, search, skip = 0, limit = 50 }) => ({
        url: '/registry/models',
        params: { project_id: projectId, search, skip, limit },
      }),
      providesTags: result =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'RegisteredModel' as const, id })),
              { type: 'RegisteredModel', id: 'LIST' },
            ]
          : [{ type: 'RegisteredModel', id: 'LIST' }],
    }),

    getModel: builder.query<RegisteredModelWithVersions, string>({
      query: modelId => `/registry/models/${modelId}`,
      providesTags: (result, error, modelId) => [{ type: 'RegisteredModel', id: modelId }],
    }),

    updateModel: builder.mutation<RegisteredModel, { id: string; data: RegisteredModelUpdate }>({
      query: ({ id, data }) => ({
        url: `/registry/models/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'RegisteredModel', id }],
    }),

    deleteModel: builder.mutation<void, string>({
      query: modelId => ({
        url: `/registry/models/${modelId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, modelId) => [
        { type: 'RegisteredModel', id: modelId },
        { type: 'RegisteredModel', id: 'LIST' },
      ],
    }),

    getRegistrySummary: builder.query<ModelRegistrySummary, string | undefined>({
      query: projectId => ({
        url: '/registry/models/summary',
        params: projectId ? { project_id: projectId } : undefined,
      }),
      providesTags: [{ type: 'RegisteredModel', id: 'SUMMARY' }],
    }),

    // Model Version endpoints
    createVersion: builder.mutation<ModelVersion, { modelId: string; data: ModelVersionCreate }>({
      query: ({ modelId, data }) => ({
        url: `/registry/models/${modelId}/versions`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (result, error, { modelId }) => [
        { type: 'RegisteredModel', id: modelId },
        { type: 'ModelVersion', id: 'LIST' },
      ],
    }),

    listVersions: builder.query<ModelVersionList, {
      modelId: string
      stage?: ModelStage
      skip?: number
      limit?: number
    }>({
      query: ({ modelId, stage, skip = 0, limit = 100 }) => ({
        url: `/registry/models/${modelId}/versions`,
        params: { stage, skip, limit },
      }),
      providesTags: (result, error, { modelId }) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'ModelVersion' as const, id })),
              { type: 'ModelVersion', id: 'LIST' },
            ]
          : [{ type: 'ModelVersion', id: 'LIST' }],
    }),

    getVersion: builder.query<ModelVersion, { modelId: string; version: string }>({
      query: ({ modelId, version }) => `/registry/models/${modelId}/versions/${version}`,
      providesTags: (result, error, { modelId, version }) => [
        { type: 'ModelVersion', id: result?.id },
      ],
    }),

    updateVersion: builder.mutation<ModelVersion, { id: string; data: ModelVersionUpdate }>({
      query: ({ id, data }) => ({
        url: `/registry/models/versions/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'ModelVersion', id }],
    }),

    deleteVersion: builder.mutation<void, string>({
      query: versionId => ({
        url: `/registry/models/versions/${versionId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, versionId) => [
        { type: 'ModelVersion', id: versionId },
        { type: 'ModelVersion', id: 'LIST' },
      ],
    }),

    // Stage Transition endpoints
    transitionStage: builder.mutation<ModelVersion, {
      versionId: string
      data: StageTransitionRequest
    }>({
      query: ({ versionId, data }) => ({
        url: `/registry/models/versions/${versionId}/transition`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (result, error, { versionId }) => [
        { type: 'ModelVersion', id: versionId },
        { type: 'RegisteredModel', id: result?.modelId },
      ],
    }),

    getTransitionHistory: builder.query<ModelVersionTransitionList, string>({
      query: versionId => `/registry/models/versions/${versionId}/transitions`,
      providesTags: (result, error, versionId) => [{ type: 'ModelVersion', id: versionId }],
    }),
  }),
})

export const {
  useCreateModelMutation,
  useListModelsQuery,
  useGetModelQuery,
  useUpdateModelMutation,
  useDeleteModelMutation,
  useGetRegistrySummaryQuery,
  useCreateVersionMutation,
  useListVersionsQuery,
  useGetVersionQuery,
  useUpdateVersionMutation,
  useDeleteVersionMutation,
  useTransitionStageMutation,
  useGetTransitionHistoryQuery,
} = modelRegistryApi
