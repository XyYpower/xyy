import { interviewApi } from './interview'
import { noteApi } from './notes'
import { reviewApi } from './review'

export async function getDashboardData() {
  const [statsRes, notesRes, sessionsRes] = await Promise.all([
    reviewApi.getStats(),
    noteApi.list({ page: 1, page_size: 5 }),
    interviewApi.list(),
  ])

  return {
    stats: statsRes.data,
    notes: notesRes.data.items,
    sessions: sessionsRes.data,
  }
}
