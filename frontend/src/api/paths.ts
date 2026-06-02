import client from './client'
import type { ApiResponse } from './notes'

export interface LearningModule {
  name: string
  topics: string[]
  priority: number
}

export interface LearningPath {
  id: string
  name: string
  description: string
  modules: LearningModule[]
  created_at: string
}

export const pathsApi = {
  generate: (goal: string) =>
    client.post<any, ApiResponse<LearningPath>>('/paths/generate', { goal }),

  list: () =>
    client.get<any, ApiResponse<LearningPath[]>>('/paths'),

  get: (id: string) =>
    client.get<any, ApiResponse<LearningPath>>(`/paths/${id}`),
}
