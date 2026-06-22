import { interviewApi } from './interview'
import { noteApi } from './notes'
import { reviewApi } from './review'

export async function getDashboardData() {
  const [statsRes, notesRes, sessionsRes] = await Promise.allSettled([
    reviewApi.getStats(),
    noteApi.list({ page: 1, page_size: 5 }),
    interviewApi.list(),
  ])

  return {
    stats: statsRes.status === 'fulfilled' ? statsRes.value.data : null,
    notes: notesRes.status === 'fulfilled' ? notesRes.value.data.items : [],
    sessions: sessionsRes.status === 'fulfilled' ? sessionsRes.value.data : [],
  }
}
