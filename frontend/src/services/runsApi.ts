import { api } from './api'
import type { Run, PaginatedResponse } from '@/types'

interface RunListParams {
  projectId?: string
  state?: 'running' | 'finished' | 'crashed' | 'killed'
  page?: number
  pageSize?: number
  search?: string
  myRuns?: boolean
}

interface RunCreateData {
  projectId: string
  name?: string
  notes?: string
  tags?: string[]
  gitCommit?: string
  gitRemote?: string
  gitBranch?: string
  host?: string
  os?: string
  pythonVersion?: string
}

export const runsApi = api.injectEndpoints({
  endpoints: builder => ({
    listRuns: builder.query<PaginatedResponse<Run>, RunListParams>({
      query: params => ({
        url: '/runs',
        params: {
          project_id: params.projectId,
          state: params.state,
          page: params.page || 1,
          page_size: params.pageSize || 20,
          search: params.search,
          my_runs: params.myRuns,
        },
      }),
      transformResponse: (response: any) => ({
        data: response.items,
        meta: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
      }),
      providesTags: result =>
        result
          ? [
              ...result.data.map(({ id }) => ({ type: 'Run' as const, id })),
              { type: 'Run', id: 'LIST' },
            ]
          : [{ type: 'Run', id: 'LIST' }],
    }),
    getRun: builder.query<Run, string>({
      query: id => `/runs/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Run', id }],
    }),
    createRun: builder.mutation<Run, RunCreateData>({
      query: data => ({
        url: '/runs',
        method: 'POST',
        body: {
          project_id: data.projectId,
          name: data.name,
          notes: data.notes,
          tags: data.tags || [],
          git_commit: data.gitCommit,
          git_remote: data.gitRemote,
          git_branch: data.gitBranch,
          host: data.host,
          os: data.os,
          python_version: data.pythonVersion,
        },
      }),
      invalidatesTags: [{ type: 'Run', id: 'LIST' }],
    }),
    updateRun: builder.mutation<
      Run,
      { id: string; data: Partial<Run> }
    >({
      query: ({ id, data }) => ({
        url: `/runs/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Run', id },
        { type: 'Run', id: 'LIST' },
      ],
    }),
    deleteRun: builder.mutation<void, string>({
      query: id => ({
        url: `/runs/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Run', id: 'LIST' }],
    }),
    finishRun: builder.mutation<
      Run,
      { id: string; exitCode?: number; summary?: Record<string, unknown> }
    >({
      query: ({ id, exitCode = 0, summary }) => ({
        url: `/runs/${id}/finish`,
        method: 'POST',
        body: {
          exit_code: exitCode,
          summary,
        },
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Run', id },
        { type: 'Run', id: 'LIST' },
      ],
    }),
    addTags: builder.mutation<Run, { id: string; tags: string[] }>({
      query: ({ id, tags }) => ({
        url: `/runs/${id}/tags`,
        method: 'POST',
        body: { tags },
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: 'Run', id }],
    }),
    removeTag: builder.mutation<Run, { id: string; tag: string }>({
      query: ({ id, tag }) => ({
        url: `/runs/${id}/tags/${tag}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: 'Run', id }],
    }),
  }),
})

export const {
  useListRunsQuery,
  useGetRunQuery,
  useCreateRunMutation,
  useUpdateRunMutation,
  useDeleteRunMutation,
  useFinishRunMutation,
  useAddTagsMutation,
  useRemoveTagMutation,
} = runsApi
