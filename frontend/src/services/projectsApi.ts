import { api } from './api'
import type { Project, ProjectFormData, PaginatedResponse } from '@/types'

interface ProjectListParams {
  page?: number
  pageSize?: number
  search?: string
  visibility?: 'public' | 'private'
  myProjects?: boolean
}

export const projectsApi = api.injectEndpoints({
  endpoints: builder => ({
    listProjects: builder.query<PaginatedResponse<Project>, ProjectListParams>({
      query: params => ({
        url: '/projects',
        params: {
          page: params.page || 1,
          page_size: params.pageSize || 20,
          search: params.search,
          visibility: params.visibility,
          my_projects: params.myProjects,
        },
      }),
      transformResponse: (response: any) => ({
        data: response.items,
        meta: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
      }),
      providesTags: result =>
        result
          ? [
              ...result.data.map(({ id }) => ({
                type: 'Project' as const,
                id,
              })),
              { type: 'Project', id: 'LIST' },
            ]
          : [{ type: 'Project', id: 'LIST' }],
    }),
    getProject: builder.query<Project, string>({
      query: id => `/projects/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Project', id }],
    }),
    createProject: builder.mutation<Project, ProjectFormData>({
      query: data => ({
        url: '/projects',
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [{ type: 'Project', id: 'LIST' }],
    }),
    updateProject: builder.mutation<
      Project,
      { id: string; data: Partial<ProjectFormData> }
    >({
      query: ({ id, data }) => ({
        url: `/projects/${id}`,
        method: 'PATCH',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Project', id },
        { type: 'Project', id: 'LIST' },
      ],
    }),
    deleteProject: builder.mutation<void, string>({
      query: id => ({
        url: `/projects/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Project', id: 'LIST' }],
    }),
  }),
})

export const {
  useListProjectsQuery,
  useGetProjectQuery,
  useCreateProjectMutation,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
} = projectsApi
