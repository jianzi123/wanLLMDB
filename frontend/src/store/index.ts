import { configureStore } from '@reduxjs/toolkit'
import authReducer from '@features/auth/authSlice'
import projectsReducer from '@features/projects/projectsSlice'
import runsReducer from '@features/runs/runsSlice'
import { api } from '@/services/api'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    projects: projectsReducer,
    runs: runsReducer,
    [api.reducerPath]: api.reducer,
  },
  middleware: getDefaultMiddleware =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['your/action/type'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['meta.arg', 'payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['items.dates'],
      },
    }).concat(api.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
