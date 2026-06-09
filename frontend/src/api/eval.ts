import client from './client'
import type { ApiResponse } from './notes'

export interface EvalCase {
  id: string
  name: string
  case_type: string
  input_data: Record<string, unknown>
  expected_output: Record<string, unknown> | null
  tags: string[] | null
  created_at: string | null
}

export interface EvalRun {
  id: string
  name: string
  target_type: string
  status: string
  total_cases: number
  passed_cases: number
  avg_score: number
  created_at: string | null
  finished_at: string | null
}

export interface EvalRunDetail extends EvalRun {
  results: EvalResultItem[]
}

export interface EvalResultItem {
  id: string
  eval_case_id: string
  score: number
  passed: boolean
  metrics: Record<string, unknown> | null
  actual_output: Record<string, unknown> | null
  error_message: string | null
}

export interface FeedbackStats {
  total: number
  helpful: number
  not_helpful: number
  helpful_rate: number
}

export const evalApi = {
  submitFeedback: (data: { message_id: string; rating: string; issue_type?: string; comment?: string }) =>
    client.post<any, ApiResponse<{ id: string; rating: string }>>('/eval/feedback', data),

  getFeedbackStats: () =>
    client.get<any, ApiResponse<FeedbackStats>>('/eval/feedback/stats'),

  createCase: (data: { name: string; case_type: string; input_data: Record<string, unknown>; expected_output?: Record<string, unknown>; tags?: string[] }) =>
    client.post<any, ApiResponse<{ id: string; name: string; case_type: string }>>('/eval/cases', data),

  listCases: (caseType?: string) =>
    client.get<any, ApiResponse<EvalCase[]>>('/eval/cases', { params: caseType ? { case_type: caseType } : {} }),

  startRun: (name?: string) =>
    client.post<any, ApiResponse<EvalRun>>('/eval/runs', { name: name || 'RAG 评估' }),

  listRuns: () =>
    client.get<any, ApiResponse<EvalRun[]>>('/eval/runs'),

  getRunDetail: (id: string) =>
    client.get<any, ApiResponse<EvalRunDetail>>(`/eval/runs/${id}`),
}
