import client from './client'
import type { ApiResponse } from './notes'

export interface PortfolioSummary {
  notes_count: number
  mastered_count: number
  review_stats: Record<string, number>
  interview_sessions: number
  agent_runs: number
  learning_paths: number
  feedback_total: number
  feedback_helpful_rate: number
}

export interface ReportSection {
  heading: string
  content: string
}

export interface ProjectReport {
  title: string
  summary: string
  sections: ReportSection[]
  highlights: string[]
  metrics: Record<string, string>
}

export interface LearningReport {
  title: string
  summary: string
  sections: ReportSection[]
  highlights: string[]
  next_steps: string[]
}

export interface RecentRun {
  id: string
  run_type: string
  goal: string | null
  status: string
  total_prompt_tokens: number
  total_completion_tokens: number
  estimated_cost: number
  created_at: string | null
  finished_at: string | null
}

export const portfolioApi = {
  getSummary: () =>
    client.get<any, ApiResponse<PortfolioSummary>>('/portfolio/summary'),

  generateProjectReport: () =>
    client.post<any, ApiResponse<ProjectReport>>('/portfolio/report/project'),

  generateLearningReport: () =>
    client.post<any, ApiResponse<LearningReport>>('/portfolio/report/learning'),

  getRecentRuns: () =>
    client.get<any, ApiResponse<RecentRun[]>>('/portfolio/runs/recent'),

  exportProjectMarkdown: () => downloadMarkdown('project'),
  exportLearningMarkdown: () => downloadMarkdown('learning'),
}

async function downloadMarkdown(type: 'project' | 'learning') {
  const { ACCESS_KEY } = await import('../store/authTokens')
  const token = localStorage.getItem(ACCESS_KEY)
  const response = await fetch(`/api/v1/portfolio/report/${type}/markdown`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error('导出失败')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `knowbase-${type}-report.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
