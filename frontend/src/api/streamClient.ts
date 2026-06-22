import { ACCESS_KEY } from '../store/authTokens'

interface StreamChatOptions {
  convId: string
  query: string
  onChunk: (text: string) => void
  onDone: (sources: { note_id: string; title: string }[]) => void
  onError: (error: Error) => void
}

/** 让出事件循环，给 React 渲染的机会 */
const yieldToMain = () => new Promise<void>((resolve) => setTimeout(resolve, 0))

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
      const errText = await response.text().catch(() => '')
      throw new Error(`请求失败：${response.status} ${errText.slice(0, 100)}`)
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
        if (!event.trim()) continue
        for (const line of event.split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const payload = JSON.parse(line.slice(6))
            if (payload.done) {
              onDone(payload.sources ?? [])
              return
            }
            if (payload.content) {
              onChunk(payload.content)
            }
          } catch {
            // ignore parse errors
          }
        }
      }

      // 关键：每读完一批数据，yield 给浏览器让 React 渲染
      await yieldToMain()
    }

    // 处理 buffer 中最后的事件
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.done) {
            onDone(payload.sources ?? [])
          } else if (payload.content) {
            onChunk(payload.content)
          }
        } catch {
          // ignore
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error : new Error('流式请求失败'))
  }
}
