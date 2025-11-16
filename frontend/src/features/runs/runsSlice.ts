import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { Run } from '@/types'

interface RunsState {
  items: Run[]
  selected: Run[]
  loading: boolean
  error: string | null
}

const initialState: RunsState = {
  items: [],
  selected: [],
  loading: false,
  error: null,
}

const runsSlice = createSlice({
  name: 'runs',
  initialState,
  reducers: {
    setRuns: (state, action: PayloadAction<Run[]>) => {
      state.items = action.payload
    },
    addRun: (state, action: PayloadAction<Run>) => {
      state.items.push(action.payload)
    },
    updateRun: (state, action: PayloadAction<Run>) => {
      const index = state.items.findIndex(r => r.id === action.payload.id)
      if (index !== -1) {
        state.items[index] = action.payload
      }
    },
    deleteRun: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(r => r.id !== action.payload)
    },
    setSelectedRuns: (state, action: PayloadAction<Run[]>) => {
      state.selected = action.payload
    },
    toggleRunSelection: (state, action: PayloadAction<Run>) => {
      const index = state.selected.findIndex(r => r.id === action.payload.id)
      if (index !== -1) {
        state.selected.splice(index, 1)
      } else {
        state.selected.push(action.payload)
      }
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
  setRuns,
  addRun,
  updateRun,
  deleteRun,
  setSelectedRuns,
  toggleRunSelection,
  setLoading,
  setError,
} = runsSlice.actions

export default runsSlice.reducer
