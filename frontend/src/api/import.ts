import client from './client'
import type { ApiResponse, Note } from './notes'

export type ImportSourceType = 'url' | 'text' | 'code'

export interface ImportJob {
  id: string
  source_type: ImportSourceType
  source_url: string | null
  status: string
  error_message: string | null
  created_at: string
}

export interface ExtractionDraft {
  id: string
  title: string
  content: string
  is_selected: boolean
  note_id: string | null
}

export interface ImportResult {
  job: ImportJob
  drafts: ExtractionDraft[]
}

export const importApi = {
  importText: (text: string, sourceUrl?: string) =>
    client.post<any, ApiResponse<ImportResult>>('/import/text', { text, source_url: sourceUrl }),

  importUrl: (url: string) =>
    client.post<any, ApiResponse<ImportResult>>('/import/url', { url }),

  importCode: (code: string, language?: string) =>
    client.post<any, ApiResponse<ImportResult>>('/import/code', { code, language }),

  getJobs: () =>
    client.get<any, ApiResponse<ImportJob[]>>('/import/jobs'),

  getDrafts: (jobId: string) =>
    client.get<any, ApiResponse<ExtractionDraft[]>>(`/import/jobs/${jobId}/drafts`),

  updateDraft: (draftId: string, data: { title?: string; content?: string; is_selected?: boolean }) =>
    client.put<any, ApiResponse<ExtractionDraft>>(`/import/drafts/${draftId}`, data),

  confirmImport: (jobId: string) =>
    client.post<any, ApiResponse<Note[]>>(`/import/jobs/${jobId}/confirm`),
}
