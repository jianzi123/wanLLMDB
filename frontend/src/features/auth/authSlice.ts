import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { User, AuthTokens } from '@/types'

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  loading: boolean
  error: string | null
}

// Load tokens from localStorage on initialization
const loadTokensFromStorage = (): AuthTokens | null => {
  try {
    const stored = localStorage.getItem('auth_tokens')
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('Failed to load tokens from storage:', error)
  }
  return null
}

// Load user from localStorage on initialization
const loadUserFromStorage = (): User | null => {
  try {
    const stored = localStorage.getItem('auth_user')
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('Failed to load user from storage:', error)
  }
  return null
}

const initialState: AuthState = {
  user: loadUserFromStorage(),
  tokens: loadTokensFromStorage(),
  loading: false,
  error: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{ user: User; tokens: AuthTokens }>
    ) => {
      state.user = action.payload.user
      state.tokens = action.payload.tokens
      state.error = null
      // Persist to localStorage
      try {
        localStorage.setItem('auth_tokens', JSON.stringify(action.payload.tokens))
        localStorage.setItem('auth_user', JSON.stringify(action.payload.user))
      } catch (error) {
        console.error('Failed to save tokens to storage:', error)
      }
    },
    logout: state => {
      state.user = null
      state.tokens = null
      state.error = null
      // Clear localStorage
      try {
        localStorage.removeItem('auth_tokens')
        localStorage.removeItem('auth_user')
      } catch (error) {
        console.error('Failed to clear tokens from storage:', error)
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

export const { setCredentials, logout, setLoading, setError } =
  authSlice.actions
export default authSlice.reducer
