import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { Project } from '@/types'

interface ProjectsState {
  items: Project[]
  selected: Project | null
  loading: boolean
  error: string | null
}

const initialState: ProjectsState = {
  items: [],
  selected: null,
  loading: false,
  error: null,
}

const projectsSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setProjects: (state, action: PayloadAction<Project[]>) => {
      state.items = action.payload
    },
    addProject: (state, action: PayloadAction<Project>) => {
      state.items.push(action.payload)
    },
    updateProject: (state, action: PayloadAction<Project>) => {
      const index = state.items.findIndex(p => p.id === action.payload.id)
      if (index !== -1) {
        state.items[index] = action.payload
      }
    },
    deleteProject: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(p => p.id !== action.payload)
    },
    setSelectedProject: (state, action: PayloadAction<Project | null>) => {
      state.selected = action.payload
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
  },
})

export const {
  setProjects,
  addProject,
  updateProject,
  deleteProject,
  setSelectedProject,
  setLoading,
  setError,
} = projectsSlice.actions

export default projectsSlice.reducer
