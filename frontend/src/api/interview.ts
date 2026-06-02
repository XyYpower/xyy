import client from './client'
import type { ApiResponse } from './notes'

export interface InterviewQuestion {
  id: string
  question: string
  user_answer: string | null
  ai_score: number | null
  ai_feedback: string | null
  question_order: number
}

export interface InterviewSession {
  id: string
  title: string
  scope: 'all' | 'weak_points'
  total_score: number | null
  summary: string | null
  status: 'in_progress' | 'completed'
  created_at: string
  finished_at: string | null
  questions: InterviewQuestion[]
}

export interface WeakPoint {
  note_id: string
  title: string
  avg_score: number
  times_tested: number
}

export const interviewApi = {
  start: (data: { scope: 'all' | 'weak_points'; num_questions: number }) =>
    client.post<any, ApiResponse<InterviewSession>>('/interview/start', data),

  submitAnswer: (sessionId: string, questionId: string, answer: string) =>
    client.post<any, ApiResponse<InterviewQuestion>>(`/interview/${sessionId}/answer/${questionId}`, { answer }),

  finish: (sessionId: string) =>
    client.post<any, ApiResponse<InterviewSession>>(`/interview/${sessionId}/finish`),

  list: () =>
    client.get<any, ApiResponse<InterviewSession[]>>('/interview/sessions'),

  get: (sessionId: string) =>
    client.get<any, ApiResponse<InterviewSession>>(`/interview/sessions/${sessionId}`),

  weakPoints: () =>
    client.get<any, ApiResponse<WeakPoint[]>>('/interview/weak-points'),
}
