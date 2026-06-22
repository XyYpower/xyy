import client from './client'
import type { ApiResponse } from './notes'

export interface User {
  id: string
  username: string
  email: string | null
  reminder_enabled: boolean
  reminder_time: string | null
  llm_provider: string | null
  llm_model: string | null
  llm_api_key_set: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export const authApi = {
  register: (data: { username: string; password: string; email?: string }) =>
    client.post<any, ApiResponse<TokenResponse>>('/auth/register', data),

  login: (data: { username: string; password: string }) =>
    client.post<any, ApiResponse<TokenResponse>>('/auth/login', data),

  refresh: (refresh_token: string) =>
    client.post<any, ApiResponse<TokenResponse>>('/auth/refresh', { refresh_token }),

  me: () =>
    client.get<any, ApiResponse<User>>('/auth/me'),

  updateProfile: (data: { email?: string; reminder_enabled?: boolean; reminder_time?: string }) =>
    client.put<any, ApiResponse<User>>('/auth/profile', data),

  changePassword: (data: { old_password: string; new_password: string }) =>
    client.put<any, ApiResponse<null>>('/auth/password', data),

  updateLLMSettings: (data: { llm_provider?: string; llm_api_key?: string; llm_model?: string }) =>
    client.put<any, ApiResponse<User>>('/auth/llm-settings', data),
}

