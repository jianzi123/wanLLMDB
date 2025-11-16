import { api } from './api'

export interface RunLog {
  id: string
  runId: string
  level: string
  message: string
  timestamp: string
  source: string
  lineNumber?: number
}

export interface RunLogList {
  items: RunLog[]
  total: number
  skip: number
  limit: number
}

export interface LogsSummary {
  total: number
  byLevel: {
    [key: string]: number
  }
}

export const runLogsApi = api.injectEndpoints({
  endpoints: builder => ({
    listRunLogs: builder.query<RunLogList, {
      runId: string
      level?: string
      source?: string
      search?: string
      skip?: number
      limit?: number
    }>({
      query: ({ runId, level, source, search, skip = 0, limit = 1000 }) => ({
        url: `/runs/${runId}/logs`,
        params: { level, source, search, skip, limit },
      }),
      providesTags: (result, error, { runId }) => [
        { type: 'RunLog', id: runId },
        { type: 'RunLog', id: 'LIST' },
      ],
    }),

    getLatestLogs: builder.query<RunLog[], { runId: string; limit?: number }>({
      query: ({ runId, limit = 100 }) => ({
        url: `/runs/${runId}/logs/latest`,
        params: { limit },
      }),
      providesTags: (result, error, { runId }) => [
        { type: 'RunLog', id: runId },
      ],
    }),

    getLogsSummary: builder.query<LogsSummary, string>({
      query: runId => `/runs/${runId}/logs/summary`,
      providesTags: (result, error, runId) => [
        { type: 'RunLog', id: runId },
      ],
    }),

    downloadLogs: builder.query<void, {
      runId: string
      format?: 'txt' | 'json' | 'csv'
      level?: string
      source?: string
      search?: string
    }>({
      query: ({ runId, format = 'txt', level, source, search }) => ({
        url: `/runs/${runId}/logs/download`,
        params: { format, level, source, search },
        responseHandler: async (response) => {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `run_${runId}_logs.${format}`
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          window.URL.revokeObjectURL(url)
        },
      }),
    }),

    deleteLogs: builder.mutation<void, string>({
      query: runId => ({
        url: `/runs/${runId}/logs`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, runId) => [
        { type: 'RunLog', id: runId },
        { type: 'RunLog', id: 'LIST' },
      ],
    }),
  }),
})

export const {
  useListRunLogsQuery,
  useGetLatestLogsQuery,
  useGetLogsSummaryQuery,
  useLazyDownloadLogsQuery,
  useDeleteLogsMutation,
} = runLogsApi
