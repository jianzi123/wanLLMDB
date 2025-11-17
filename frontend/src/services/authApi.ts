import { api } from './api'
import type { User, AuthTokens, LoginFormData, RegisterFormData } from '@/types'

export const authApi = api.injectEndpoints({
  endpoints: builder => ({
    login: builder.mutation<AuthTokens, LoginFormData>({
      query: credentials => ({
        url: '/auth/login',
        method: 'POST',
        body: new URLSearchParams({
          username: credentials.username,
          password: credentials.password,
        }),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }),
      transformResponse: (response: any): AuthTokens => {
        // Convert snake_case to camelCase
        return {
          accessToken: response.access_token || response.accessToken,
          refreshToken: response.refresh_token || response.refreshToken,
          tokenType: response.token_type || response.tokenType || 'bearer',
        }
      },
    }),
    register: builder.mutation<User, RegisterFormData>({
      query: userData => ({
        url: '/auth/register',
        method: 'POST',
        body: {
          username: userData.username,
          email: userData.email,
          password: userData.password,
          full_name: userData.fullName, // Convert camelCase to snake_case for backend
        },
      }),
    }),
    getMe: builder.query<User, void>({
      query: () => '/auth/me',
      providesTags: ['User'],
    }),
  }),
})

export const { useLoginMutation, useRegisterMutation, useGetMeQuery } = authApi
