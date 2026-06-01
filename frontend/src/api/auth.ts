import client from './client'
import type { ApiResponse } from './notes'

export interface User {
  id: string
  username: string
  email: string | null
  reminder_enabled: boolean
  reminder_time: string | null
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
}

