import client from './client'
import type { ApiResponse } from './notes'

export interface Category {
  id: string
  name: string
  description: string | null
  sort_order: number
}

export const categoryApi = {
  list: () =>
    client.get<any, ApiResponse<Category[]>>('/categories'),

  create: (data: { name: string; description?: string }) =>
    client.post<any, ApiResponse<Category>>('/categories', data),

  update: (id: string, data: { name?: string; description?: string; sort_order?: number }) =>
    client.put<any, ApiResponse<Category>>(`/categories/${id}`, data),

  delete: (id: string) =>
    client.delete<any, ApiResponse<null>>(`/categories/${id}`),
}
