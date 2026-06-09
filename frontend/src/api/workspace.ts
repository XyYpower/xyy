import client from './client'
import type { ApiResponse } from './notes'

export interface DiagnosisResult {
  weak_areas: Array<{
    area: string
    reason: string
    priority: number
    suggested_topics: string[]
  }>
  summary: string
  next_steps: string[]
}

export interface PlanResult {
  path_id: string
  name: string
  description: string
  modules_count: number
  tasks_count: number
  tasks: Array<{
    title: string
    task_type: string
    due_at: string | null
  }>
}

export interface LearningTask {
  id: string
  title: string
  description: string
  task_type: string
  status: string
  due_at: string | null
  completed_at: string | null
  topic_id: string | null
  topic_title?: string | null
}

export const workspaceApi = {
  diagnose: () =>
    client.post<any, ApiResponse<{ run_id: string; diagnosis: DiagnosisResult }>>('/workspace/diagnose'),

  plan: (goal: string, runDiagnosisFirst = true) =>
    client.post<any, ApiResponse<{ run_id: string; plan: PlanResult; diagnosis: DiagnosisResult | null }>>(
      '/workspace/plan', null, { params: { goal, run_diagnosis_first: runDiagnosisFirst } }
    ),

  diagnoseAndPlan: (goal: string) =>
    client.post<any, ApiResponse<{ run_id: string; diagnosis: DiagnosisResult; plan: PlanResult }>>(
      '/workspace/diagnose-and-plan', null, { params: { goal } }
    ),

  getTodayTasks: () =>
    client.get<any, ApiResponse<{ tasks: LearningTask[]; total: number }>>('/workspace/tasks/today'),

  listTasks: (params?: { status_filter?: string; page?: number; page_size?: number }) =>
    client.get<any, ApiResponse<{ items: LearningTask[]; total: number; page: number; page_size: number }>>(
      '/workspace/tasks', { params }
    ),

  completeTask: (taskId: string) =>
    client.put<any, ApiResponse<{ id: string; status: string }>>(`/workspace/tasks/${taskId}/complete`),
}
