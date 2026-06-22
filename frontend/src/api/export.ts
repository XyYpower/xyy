import { ACCESS_KEY } from '../store/authTokens'

type ExportType = 'json' | 'markdown'

const filenameMap: Record<ExportType, string> = {
  json: 'knowbase-export.json',
  markdown: 'knowbase-notes.md',
}

export async function downloadExport(type: ExportType): Promise<void> {
  const token = localStorage.getItem(ACCESS_KEY)
  const response = await fetch(`/api/v1/export/${type}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error(`导出失败：${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filenameMap[type]
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
