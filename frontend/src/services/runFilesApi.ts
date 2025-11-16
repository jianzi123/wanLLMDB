import { api } from './api'

export interface RunFile {
  id: string
  runId: string
  name: string
  path: string
  size: number
  contentType?: string
  storageKey: string
  md5Hash?: string
  sha256Hash?: string
  description?: string
  createdAt: string
  updatedAt: string
}

export interface RunFileList {
  items: RunFile[]
  total: number
  skip: number
  limit: number
}

export interface FileDownloadUrlResponse {
  downloadUrl: string
  filename: string
  size: number
  contentType?: string
  expiresIn: number
}

export const runFilesApi = api.injectEndpoints({
  endpoints: builder => ({
    listRunFiles: builder.query<RunFileList, { runId: string; skip?: number; limit?: number }>({
      query: ({ runId, skip = 0, limit = 100 }) => ({
        url: `/runs/${runId}/files`,
        params: { skip, limit },
      }),
      providesTags: (result, error, { runId }) => [
        { type: 'RunFile', id: runId },
        { type: 'RunFile', id: 'LIST' },
      ],
    }),

    getRunFile: builder.query<RunFile, string>({
      query: fileId => `/runs/files/${fileId}`,
      providesTags: (result, error, fileId) => [{ type: 'RunFile', id: fileId }],
    }),

    getFileDownloadUrl: builder.query<FileDownloadUrlResponse, string>({
      query: fileId => `/runs/files/${fileId}/download-url`,
    }),

    deleteRunFile: builder.mutation<void, string>({
      query: fileId => ({
        url: `/runs/files/${fileId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, fileId) => [
        { type: 'RunFile', id: fileId },
        { type: 'RunFile', id: 'LIST' },
      ],
    }),
  }),
})

export const {
  useListRunFilesQuery,
  useGetRunFileQuery,
  useGetFileDownloadUrlQuery,
  useLazyGetFileDownloadUrlQuery,
  useDeleteRunFileMutation,
} = runFilesApi
