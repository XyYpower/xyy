import client from './client'

export interface Note {
  id: string
  title: string
  content: string
  summary: string | null
  category: { id: string; name: string; description?: string | null; sort_order?: number } | null
  tags: { id: string; name: string }[]
  is_favorite: boolean
  mastery_level: number
  source_type: string
  source_url: string | null
  created_at: string
  updated_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export const noteApi = {
  list: (params?: {
    page?: number
    page_size?: number
    keyword?: string
    category_id?: string
    tag_id?: string
    mastery_level?: number
    source_type?: string
    is_favorite?: boolean
  }) =>
    client.get<any, ApiResponse<PageResult<Note>>>('/notes', { params }),

  get: (id: string) =>
    client.get<any, ApiResponse<Note>>(`/notes/${id}`),

  create: (data: {
    title: string
    content?: string
    tag_names?: string[]
    category_id?: string | null
    is_favorite?: boolean
    mastery_level?: number
  }) =>
    client.post<any, ApiResponse<Note>>('/notes', data),

  update: (id: string, data: Partial<{
    title: string
    content: string
    tag_names: string[]
    category_id: string | null
    is_favorite: boolean
    mastery_level: number
  }>) =>
    client.put<any, ApiResponse<Note>>(`/notes/${id}`, data),

  delete: (id: string) =>
    client.delete<any, ApiResponse<null>>(`/notes/${id}`),
}
