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
    }),
    register: builder.mutation<User, RegisterFormData>({
      query: userData => ({
        url: '/auth/register',
        method: 'POST',
        body: userData,
      }),
    }),
    getMe: builder.query<User, void>({
      query: () => '/auth/me',
      providesTags: ['User'],
    }),
  }),
})

export const { useLoginMutation, useRegisterMutation, useGetMeQuery } = authApi
