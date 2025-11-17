import { configureStore } from '@reduxjs/toolkit'
import authReducer from '@features/auth/authSlice'
import projectsReducer from '@features/projects/projectsSlice'
import runsReducer from '@features/runs/runsSlice'
import { api } from '@/services/api'
import { metricApi } from '@/services/metricsApi'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    projects: projectsReducer,
    runs: runsReducer,
    [api.reducerPath]: api.reducer,
    [metricApi.reducerPath]: metricApi.reducer,
  },
  middleware: getDefaultMiddleware =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['your/action/type'],
        // Ignore these field paths in all actions (RTK Query includes Request objects)
        ignoredActionPaths: ['meta.arg', 'payload.timestamp', 'meta.baseQueryMeta.request', 'meta.baseQueryMeta.response'],
        // Ignore these paths in the state
        ignoredPaths: ['items.dates'],
      },
    }).concat(api.middleware, metricApi.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
