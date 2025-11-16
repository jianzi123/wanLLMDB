import { api } from './api'
import type {
  Sweep,
  SweepList,
  SweepFormData,
  SweepWithStats,
  SweepStats,
  SweepRunDetail,
  SweepSuggestResponse,
  ParallelCoordinatesData,
  SweepState,
} from '@/types'

interface SweepListParams {
  page?: number
  pageSize?: number
  projectId?: string
  state?: SweepState
}

interface SweepUpdateData {
  name?: string
  description?: string
  state?: SweepState
  runCap?: number
}

interface SweepRunsListParams {
  sweepId: string
  page?: number
  pageSize?: number
}

export const sweepsApi = api.injectEndpoints({
  endpoints: builder => ({
    // Sweep CRUD operations
    listSweeps: builder.query<SweepList, SweepListParams>({
      query: params => ({
        url: '/sweeps',
        params: {
          page: params.page || 1,
          page_size: params.pageSize || 20,
          project_id: params.projectId,
          state: params.state,
        },
      }),
      providesTags: result =>
        result
          ? [
              ...result.items.map(({ id }) => ({
                type: 'Sweep' as const,
                id,
              })),
              { type: 'Sweep', id: 'LIST' },
            ]
          : [{ type: 'Sweep', id: 'LIST' }],
    }),

    getSweep: builder.query<SweepWithStats, string>({
      query: sweepId => `/sweeps/${sweepId}`,
      providesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    createSweep: builder.mutation<Sweep, SweepFormData>({
      query: data => ({
        url: '/sweeps',
        method: 'POST',
        body: {
          name: data.name,
          description: data.description,
          project_id: data.projectId,
          method: data.method,
          metric_name: data.metricName,
          metric_goal: data.metricGoal,
          config: data.config,
          early_terminate: data.earlyTerminate,
          run_cap: data.runCap,
        },
      }),
      invalidatesTags: [{ type: 'Sweep', id: 'LIST' }],
    }),

    updateSweep: builder.mutation<Sweep, { id: string; data: SweepUpdateData }>({
      query: ({ id, data }) => ({
        url: `/sweeps/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Sweep', id },
        { type: 'Sweep', id: 'LIST' },
      ],
    }),

    deleteSweep: builder.mutation<void, string>({
      query: id => ({
        url: `/sweeps/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: (_result, _error, id) => [
        { type: 'Sweep', id },
        { type: 'Sweep', id: 'LIST' },
      ],
    }),

    // Sweep lifecycle operations
    startSweep: builder.mutation<Sweep, string>({
      query: sweepId => ({
        url: `/sweeps/${sweepId}/start`,
        method: 'POST',
      }),
      invalidatesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    pauseSweep: builder.mutation<Sweep, string>({
      query: sweepId => ({
        url: `/sweeps/${sweepId}/pause`,
        method: 'POST',
      }),
      invalidatesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    resumeSweep: builder.mutation<Sweep, string>({
      query: sweepId => ({
        url: `/sweeps/${sweepId}/resume`,
        method: 'POST',
      }),
      invalidatesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    finishSweep: builder.mutation<Sweep, string>({
      query: sweepId => ({
        url: `/sweeps/${sweepId}/finish`,
        method: 'POST',
      }),
      invalidatesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    // Parameter suggestion
    suggestParameters: builder.mutation<SweepSuggestResponse, string>({
      query: sweepId => ({
        url: `/sweeps/${sweepId}/suggest`,
        method: 'POST',
        body: { sweep_id: sweepId },
      }),
    }),

    // Statistics and visualization
    getSweepStats: builder.query<SweepStats, string>({
      query: sweepId => `/sweeps/${sweepId}/stats`,
      providesTags: (_result, _error, id) => [{ type: 'Sweep', id }],
    }),

    getParallelCoordinatesData: builder.query<ParallelCoordinatesData, string>({
      query: sweepId => `/sweeps/${sweepId}/parallel-coordinates`,
      providesTags: (_result, _error, sweepId) => [{ type: 'Sweep', id: sweepId }],
    }),

    // Sweep runs
    listSweepRuns: builder.query<
      { items: SweepRunDetail[]; total: number; page: number; pageSize: number; totalPages: number },
      SweepRunsListParams
    >({
      query: ({ sweepId, page = 1, pageSize = 100 }) => ({
        url: `/sweeps/${sweepId}/runs`,
        params: {
          page,
          page_size: pageSize,
        },
      }),
      providesTags: (result, _error, { sweepId }) =>
        result
          ? [
              ...result.items.map(({ id }) => ({
                type: 'SweepRun' as const,
                id,
              })),
              { type: 'SweepRun', id: `LIST-${sweepId}` },
            ]
          : [{ type: 'SweepRun', id: `LIST-${sweepId}` }],
    }),
  }),
})

export const {
  useListSweepsQuery,
  useGetSweepQuery,
  useCreateSweepMutation,
  useUpdateSweepMutation,
  useDeleteSweepMutation,
  useStartSweepMutation,
  usePauseSweepMutation,
  useResumeSweepMutation,
  useFinishSweepMutation,
  useSuggestParametersMutation,
  useGetSweepStatsQuery,
  useGetParallelCoordinatesDataQuery,
  useListSweepRunsQuery,
} = sweepsApi
