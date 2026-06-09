import client from './client'
import type { ApiResponse } from './notes'

export interface AgentRun {
  id: string
  run_type: string
  goal: string | null
  status: string
  current_step: string | null
  total_prompt_tokens: number
  total_completion_tokens: number
  estimated_cost: number
  error_message: string | null
  created_at: string | null
  finished_at: string | null
}

export interface AgentRunDetail extends AgentRun {
  input: Record<string, unknown> | null
  output: Record<string, unknown> | null
  steps: AgentStep[]
  tool_calls: ToolCallRecord[]
}

export interface AgentStep {
  id: string
  step_order: number
  agent_name: string
  node_name: string
  status: string
  input: Record<string, unknown> | null
  output: Record<string, unknown> | null
  reasoning_summary: string | null
  requires_approval: boolean
  latency_ms: number | null
  error_message: string | null
}

export interface ToolCallRecord {
  id: string
  step_id: string | null
  tool_name: string
  arguments: Record<string, unknown> | null
  result: Record<string, unknown> | null
  status: string
  latency_ms: number | null
  error_message: string | null
}

export interface AICallLog {
  id: string
  provider: string
  model: string
  purpose: string
  prompt_tokens: number
  completion_tokens: number
  estimated_cost: number
  latency_ms: number
  status: string
  error_message: string | null
  created_at: string | null
}

export interface TraceStats {
  total_runs: number
  completed_runs: number
  success_rate: number
  total_prompt_tokens: number
  total_completion_tokens: number
  total_cost: number
  total_ai_calls: number
  ai_prompt_tokens: number
  ai_completion_tokens: number
  ai_cost: number
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const traceApi = {
  listRuns: (params?: { page?: number; page_size?: number }) =>
    client.get<any, ApiResponse<PageResult<AgentRun>>>('/traces/runs', { params }),

  getRunDetail: (id: string) =>
    client.get<any, ApiResponse<AgentRunDetail>>(`/traces/runs/${id}`),

  listAILogs: (params?: { page?: number; page_size?: number }) =>
    client.get<any, ApiResponse<PageResult<AICallLog>>>('/traces/ai-logs', { params }),

  getStats: () =>
    client.get<any, ApiResponse<TraceStats>>('/traces/stats'),
}
