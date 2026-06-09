import client from './client'
import type { ApiResponse } from './notes'

export interface Tag {
  id: string
  name: string
}

export const tagApi = {
  list: () =>
    client.get<any, ApiResponse<Tag[]>>('/tags'),
}
