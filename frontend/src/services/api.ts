import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from '@/store'

const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    // Get token from state
    const token = (getState() as RootState).auth.tokens?.accessToken
    if (token) {
      headers.set('authorization', `Bearer ${token}`)
    }
    return headers
  },
})

export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Project', 'Run', 'RunFile', 'Artifact', 'ArtifactVersion', 'ArtifactFile', 'Sweep', 'SweepRun'],
  endpoints: () => ({}),
})
