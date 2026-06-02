import { ACCESS_KEY } from '../store/authTokens'

interface StreamChatOptions {
  convId: string
  query: string
  onChunk: (text: string) => void
  onDone: (sources: { note_id: string; title: string }[]) => void
  onError: (error: Error) => void
}

export async function streamChat({ convId, query, onChunk, onDone, onError }: StreamChatOptions): Promise<void> {
  try {
    const token = localStorage.getItem(ACCESS_KEY)
    const response = await fetch(`/api/v1/chat/conversations/${convId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query }),
    })

    if (!response.ok || !response.body) {
      throw new Error(`流式请求失败：${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() ?? ''

      for (const event of events) {
        const line = event.split('\n').find((item) => item.startsWith('data: '))
        if (!line) continue
        const payload = JSON.parse(line.slice(6))
        if (payload.done) {
          onDone(payload.sources ?? [])
        } else if (payload.content) {
          onChunk(payload.content)
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error('流式请求失败'))
  }
}
