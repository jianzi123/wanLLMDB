import { api } from './api'
import type {
  Artifact,
  ArtifactList,
  ArtifactFormData,
  ArtifactVersion,
  ArtifactVersionList,
  ArtifactVersionFormData,
  ArtifactVersionWithFiles,
  ArtifactFile,
  FileUploadRequest,
  FileUploadResponse,
  FileDownloadResponse,
  ArtifactType,
} from '@/types'

interface ArtifactListParams {
  page?: number
  pageSize?: number
  projectId?: string
  artifactType?: ArtifactType
  search?: string
}

interface ArtifactVersionListParams {
  artifactId: string
  page?: number
  pageSize?: number
}

interface FileUploadUrlParams {
  versionId: string
  request: FileUploadRequest
}

interface AddFileParams {
  versionId: string
  file: {
    path: string
    name: string
    size: number
    storageKey: string
    mimeType?: string
    md5Hash?: string
    sha256Hash?: string
  }
}

interface FinalizeVersionParams {
  versionId: string
  digest?: string
}

// Alias types
export interface ArtifactAlias {
  id: string
  artifactId: string
  versionId: string
  alias: string
  createdBy: string
  createdAt: string
  updatedAt: string
}

export interface ArtifactAliasWithVersion extends ArtifactAlias {
  version?: ArtifactVersion
}

export interface ArtifactAliasList {
  items: ArtifactAlias[]
  total: number
}

interface CreateAliasParams {
  artifactId: string
  data: {
    alias: string
    versionId: string
  }
}

interface GetAliasParams {
  artifactId: string
  alias: string
}

interface DeleteAliasParams {
  artifactId: string
  alias: string
}

export const artifactsApi = api.injectEndpoints({
  endpoints: builder => ({
    // Artifact endpoints
    listArtifacts: builder.query<ArtifactList, ArtifactListParams>({
      query: params => ({
        url: '/artifacts',
        params: {
          page: params.page || 1,
          page_size: params.pageSize || 20,
          project_id: params.projectId,
          artifact_type: params.artifactType,
          search: params.search,
        },
      }),
      providesTags: result =>
        result
          ? [
              ...result.items.map(({ id }) => ({
                type: 'Artifact' as const,
                id,
              })),
              { type: 'Artifact', id: 'LIST' },
            ]
          : [{ type: 'Artifact', id: 'LIST' }],
    }),

    getArtifact: builder.query<Artifact, string>({
      query: id => `/artifacts/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Artifact', id }],
    }),

    createArtifact: builder.mutation<Artifact, ArtifactFormData>({
      query: data => ({
        url: '/artifacts',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Artifact', id: 'LIST' }],
    }),

    updateArtifact: builder.mutation<
      Artifact,
      { id: string; data: Partial<ArtifactFormData> }
    >({
      query: ({ id, data }) => ({
        url: `/artifacts/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Artifact', id },
        { type: 'Artifact', id: 'LIST' },
      ],
    }),

    deleteArtifact: builder.mutation<void, string>({
      query: id => ({
        url: `/artifacts/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: 'Artifact', id },
        { type: 'Artifact', id: 'LIST' },
        { type: 'ArtifactVersion', id: 'LIST' },
      ],
    }),

    // Artifact version endpoints
    listArtifactVersions: builder.query<ArtifactVersionList, ArtifactVersionListParams>({
      query: ({ artifactId, ...params }) => ({
        url: `/artifacts/${artifactId}/versions`,
        params: {
          page: params.page || 1,
          page_size: params.pageSize || 20,
        },
      }),
      providesTags: (result, _error, { artifactId }) =>
        result
          ? [
              ...result.items.map(({ id }) => ({
                type: 'ArtifactVersion' as const,
                id,
              })),
              { type: 'ArtifactVersion', id: `LIST-${artifactId}` },
            ]
          : [{ type: 'ArtifactVersion', id: `LIST-${artifactId}` }],
    }),

    getArtifactVersion: builder.query<ArtifactVersionWithFiles, string>({
      query: versionId => `/artifacts/versions/${versionId}`,
      providesTags: (_result, _error, id) => [{ type: 'ArtifactVersion', id }],
    }),

    createArtifactVersion: builder.mutation<
      ArtifactVersion,
      { artifactId: string; data: ArtifactVersionFormData }
    >({
      query: ({ artifactId, data }) => ({
        url: `/artifacts/${artifactId}/versions`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (_result, _error, { artifactId }) => [
        { type: 'Artifact', id: artifactId },
        { type: 'ArtifactVersion', id: `LIST-${artifactId}` },
      ],
    }),

    finalizeVersion: builder.mutation<ArtifactVersion, FinalizeVersionParams>({
      query: ({ versionId, digest }) => ({
        url: `/artifacts/versions/${versionId}/finalize`,
        method: 'POST',
        body: { digest },
      }),
      invalidatesTags: (_result, _error, { versionId }) => [
        { type: 'ArtifactVersion', id: versionId },
      ],
    }),

    // File upload/download endpoints
    getFileUploadUrl: builder.mutation<FileUploadResponse, FileUploadUrlParams>({
      query: ({ versionId, request }) => ({
        url: `/artifacts/versions/${versionId}/files/upload-url`,
        method: 'POST',
        body: request,
      }),
    }),

    addFileToVersion: builder.mutation<ArtifactFile, AddFileParams>({
      query: ({ versionId, file }) => ({
        url: `/artifacts/versions/${versionId}/files`,
        method: 'POST',
        body: {
          version_id: versionId,
          ...file,
        },
      }),
      invalidatesTags: (_result, _error, { versionId }) => [
        { type: 'ArtifactVersion', id: versionId },
      ],
    }),

    getFileDownloadUrl: builder.query<FileDownloadResponse, string>({
      query: fileId => `/artifacts/files/${fileId}/download-url`,
    }),

    deleteFile: builder.mutation<void, string>({
      query: fileId => ({
        url: `/artifacts/files/${fileId}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'ArtifactVersion', id: 'LIST' }],
    }),

    // Alias endpoints
    createAlias: builder.mutation<ArtifactAlias, CreateAliasParams>({
      query: ({ artifactId, data }) => ({
        url: `/artifacts/${artifactId}/aliases`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: (_result, _error, { artifactId }) => [
        { type: 'Artifact', id: artifactId },
        { type: 'ArtifactAlias', id: `LIST-${artifactId}` },
      ],
    }),

    listAliases: builder.query<ArtifactAliasList, string>({
      query: artifactId => `/artifacts/${artifactId}/aliases`,
      providesTags: (result, _error, artifactId) =>
        result
          ? [
              ...result.items.map(({ id }) => ({
                type: 'ArtifactAlias' as const,
                id,
              })),
              { type: 'ArtifactAlias', id: `LIST-${artifactId}` },
            ]
          : [{ type: 'ArtifactAlias', id: `LIST-${artifactId}` }],
    }),

    getAlias: builder.query<ArtifactAliasWithVersion, GetAliasParams>({
      query: ({ artifactId, alias }) => `/artifacts/${artifactId}/aliases/${alias}`,
      providesTags: (result, _error, { artifactId, alias }) => [
        { type: 'ArtifactAlias', id: `${artifactId}-${alias}` },
      ],
    }),

    deleteAlias: builder.mutation<void, DeleteAliasParams>({
      query: ({ artifactId, alias }) => ({
        url: `/artifacts/${artifactId}/aliases/${alias}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, { artifactId }) => [
        { type: 'Artifact', id: artifactId },
        { type: 'ArtifactAlias', id: `LIST-${artifactId}` },
      ],
    }),
  }),
})

export const {
  useListArtifactsQuery,
  useGetArtifactQuery,
  useCreateArtifactMutation,
  useUpdateArtifactMutation,
  useDeleteArtifactMutation,
  useListArtifactVersionsQuery,
  useGetArtifactVersionQuery,
  useCreateArtifactVersionMutation,
  useFinalizeVersionMutation,
  useGetFileUploadUrlMutation,
  useAddFileToVersionMutation,
  useGetFileDownloadUrlQuery,
  useLazyGetFileDownloadUrlQuery,
  useDeleteFileMutation,
  useCreateAliasMutation,
  useListAliasesQuery,
  useGetAliasQuery,
  useDeleteAliasMutation,
} = artifactsApi
