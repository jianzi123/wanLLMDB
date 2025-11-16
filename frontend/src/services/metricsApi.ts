import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from '@/store'
import type { Metric, MetricStats } from '@/types'

// Separate API for metric service (runs on port 8001)
const metricApi = createApi({
  reducerPath: 'metricApi',
  baseQuery: fetchBaseQuery({
    baseUrl: 'http://localhost:8001/api/v1',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.tokens?.accessToken
      if (token) {
        headers.set('authorization', `Bearer ${token}`)
      }
      return headers
    },
  }),
  tagTypes: ['Metric'],
  endpoints: () => ({}),
})

export interface BatchMetricRequest {
  metrics: {
    run_id: string
    metric_name: string
    step?: number
    value: number
    time?: string
    metadata?: Record<string, any>
  }[]
}

export interface MetricQueryParams {
  start_time?: string
  end_time?: string
  min_step?: number
  max_step?: number
  limit?: number
  metric_name?: string
}

export interface RunMetricsResponse {
  run_id: string
  metrics: Metric[]
  count: number
}

export interface MetricHistoryResponse {
  run_id: string
  metric_name: string
  metrics: Metric[]
  count: number
}

export const metricsApi = metricApi.injectEndpoints({
  endpoints: (builder) => ({
    // Batch write metrics
    batchWriteMetrics: builder.mutation<{ message: string; count: number }, BatchMetricRequest>({
      query: (data) => ({
        url: '/metrics/batch',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Metric', id: 'LIST' }],
    }),

    // Get all metrics for a run
    getRunMetrics: builder.query<RunMetricsResponse, { runId: string; params?: MetricQueryParams }>({
      query: ({ runId, params }) => ({
        url: `/runs/${runId}/metrics`,
        params,
      }),
      providesTags: (result, error, { runId }) => [{ type: 'Metric', id: runId }],
    }),

    // Get metric history
    getMetricHistory: builder.query<MetricHistoryResponse, { runId: string; metricName: string; params?: MetricQueryParams }>({
      query: ({ runId, metricName, params }) => ({
        url: `/runs/${runId}/metrics/${metricName}`,
        params,
      }),
      providesTags: (result, error, { runId, metricName }) => [
        { type: 'Metric', id: runId },
        { type: 'Metric', id: `${runId}-${metricName}` },
      ],
    }),

    // Get latest metric value
    getLatestMetric: builder.query<Metric, { runId: string; metricName: string }>({
      query: ({ runId, metricName }) => ({
        url: `/runs/${runId}/metrics/${metricName}/latest`,
      }),
      providesTags: (result, error, { runId, metricName }) => [{ type: 'Metric', id: `${runId}-${metricName}-latest` }],
    }),

    // Get metric statistics
    getMetricStats: builder.query<MetricStats, { runId: string; metricName: string }>({
      query: ({ runId, metricName }) => ({
        url: `/runs/${runId}/metrics/${metricName}/stats`,
      }),
      providesTags: (result, error, { runId, metricName }) => [{ type: 'Metric', id: `${runId}-${metricName}-stats` }],
    }),
  }),
  overrideExisting: false,
})

export const {
  useBatchWriteMetricsMutation,
  useGetRunMetricsQuery,
  useGetMetricHistoryQuery,
  useGetLatestMetricQuery,
  useGetMetricStatsQuery,
} = metricsApi

export { metricApi }
