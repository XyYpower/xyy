import client from './client'
import type { ApiResponse } from './notes'

export interface ReviewCard {
  id: string
  note_id: string
  card_type: 'concept' | 'code' | 'scenario'
  question: string
  answer: string
  next_review_at: string | null
  ease_factor: number
  interval_days: number
  review_count: number
  is_user_edited: boolean
  is_flagged: boolean
  created_at: string
}

export interface ReviewStats {
  total_cards: number
  due_today: number
  mastered_count: number
  learning_count: number
  new_count: number
}

export const reviewApi = {
  getToday: () =>
    client.get<any, ApiResponse<ReviewCard[]>>('/review/today'),

  getCards: (noteId: string) =>
    client.get<any, ApiResponse<ReviewCard[]>>(`/review/cards/${noteId}`),

  submitReview: (cardId: string, quality: number) =>
    client.post<any, ApiResponse<ReviewCard>>('/review/submit', { card_id: cardId, quality }),

  getStats: () =>
    client.get<any, ApiResponse<ReviewStats>>('/review/stats'),

  generateCards: (noteId: string) =>
    client.post<any, ApiResponse<ReviewCard[]>>(`/review/generate/${noteId}`),

  editCard: (cardId: string, data: { question: string; answer: string }) =>
    client.put<any, ApiResponse<ReviewCard>>(`/review/cards/${cardId}`, data),

  flagCard: (cardId: string) =>
    client.post<any, ApiResponse<ReviewCard>>(`/review/cards/${cardId}/flag`),
}

