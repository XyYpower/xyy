import client from './client'
import type { ApiResponse } from './notes'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  sources: { note_id: string; title: string }[] | null
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  note_id: string | null
  created_at: string
  updated_at: string
  messages: Message[]
}

export const chatApi = {
  list: () =>
    client.get<any, ApiResponse<Conversation[]>>('/chat/conversations'),

  create: (noteId?: string) =>
    client.post<any, ApiResponse<Conversation>>('/chat/conversations', { note_id: noteId ?? null }),

  get: (id: string) =>
    client.get<any, ApiResponse<Conversation>>(`/chat/conversations/${id}`),

  delete: (id: string) =>
    client.delete<any, ApiResponse<null>>(`/chat/conversations/${id}`),
}
