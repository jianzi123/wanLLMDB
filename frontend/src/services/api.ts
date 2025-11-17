import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from '@/store'

const baseQuery = fetchBaseQuery({
  baseUrl: '/api/v1',
  prepareHeaders: (headers, { getState }) => {
    // Get token from state
    const state = getState() as RootState
    const token = state.auth.tokens?.accessToken
    if (token) {
      headers.set('authorization', `Bearer ${token}`)
      console.log('API: Adding token to request:', token.substring(0, 20) + '...')
    } else {
      console.warn('API: No token found in state')
    }
    return headers
  },
})

export const api = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['User', 'Project', 'Run', 'RunFile', 'RunLog', 'Artifact', 'ArtifactVersion', 'ArtifactFile', 'ArtifactAlias', 'Sweep', 'SweepRun', 'RegisteredModel', 'ModelVersion'],
  endpoints: () => ({}),
})
