import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Empty, Input, List, Space, Tag, Typography, message } from 'antd'
import { DeleteOutlined, MessageOutlined, PlusOutlined, SendOutlined, LikeOutlined, DislikeOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { chatApi, type Conversation, type Message } from '../api/chat'
import { streamChat } from '../api/streamClient'
import { evalApi } from '../api/eval'

const { Text, Title } = Typography
const { TextArea } = Input

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [query, setQuery] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId) ?? null,
    [activeId, conversations],
  )

  const fetchConversations = async () => {
    setLoading(true)
    try {
      const response = await chatApi.list()
      setConversations(response.data)
      if (!activeId && response.data.length > 0) {
        setActiveId(response.data[0].id)
      }
    } catch {
      message.error('加载对话列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (!activeId) {
      setMessages([])
      return
    }
    const fetchDetail = async () => {
      try {
        const response = await chatApi.get(activeId)
        setMessages(response.data.messages)
      } catch {
        message.error('加载对话失败')
      }
    }
    fetchDetail()
  }, [activeId])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const createConversation = async () => {
    try {
      const response = await chatApi.create()
      setConversations((current) => [response.data, ...current])
      setActiveId(response.data.id)
      setMessages([])
    } catch {
      message.error('创建对话失败')
    }
  }

  const deleteConversation = async (id: string) => {
    try {
      await chatApi.delete(id)
      setConversations((current) => current.filter((item) => item.id !== id))
      if (activeId === id) {
        const next = conversations.find((item) => item.id !== id)
        setActiveId(next?.id ?? null)
      }
    } catch {
      message.error('删除对话失败')
    }
  }

  const send = async () => {
    const content = query.trim()
    if (!content || streaming) return

    let conversationId = activeId
    if (!conversationId) {
      try {
        const created = await chatApi.create()
        conversationId = created.data.id
        setConversations((current) => [created.data, ...current])
        setActiveId(conversationId)
      } catch {
        message.error('创建对话失败')
        return
      }
    }

    const now = new Date().toISOString()
    const userMessage: Message = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content,
      sources: null,
      created_at: now,
    }
    const assistantMessage: Message = {
      id: `local-assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      sources: null,
      created_at: now,
    }

    setQuery('')
    setStreaming(true)
    setMessages((current) => [...current, userMessage, assistantMessage])

    await streamChat({
      convId: conversationId,
      query: content,
      onChunk: (chunk) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantMessage.id ? { ...item, content: item.content + chunk } : item,
          ),
        )
      },
      onDone: (sources) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantMessage.id ? { ...item, sources } : item,
          ),
        )
        fetchConversations()
      },
      onError: (error) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantMessage.id
              ? {
                  ...item,
                  content: `发送失败：${error.message}`,
                  sources: null,
                }
              : item,
          ),
        )
        message.error(error.message)
      },
    })
    setStreaming(false)
  }

  return (
    <div className="h-[calc(100vh-48px)] min-h-[640px]">
      <div className="flex justify-between items-start mb-5">
        <div>
          <Title level={2} className="!mb-1">AI 对话</Title>
          <Text type="secondary">基于你的知识点检索回答，回复会附带引用来源</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={createConversation}>
          新对话
        </Button>
      </div>

      <div className="grid grid-cols-[280px_1fr] gap-4 h-[calc(100%-84px)]">
        <aside className="bg-white border border-gray-200 rounded-lg overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-100 font-medium">对话列表</div>
          <div className="flex-1 overflow-y-auto">
            <List
              loading={loading}
              dataSource={conversations}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对话" /> }}
              renderItem={(conversation) => (
                <List.Item
                  className={`!px-3 !py-2 cursor-pointer ${activeId === conversation.id ? 'bg-blue-50' : ''}`}
                  onClick={() => setActiveId(conversation.id)}
                  actions={[
                    <Button
                      key="delete"
                      type="text"
                      size="small"
                      icon={<DeleteOutlined />}
                      onClick={(event) => {
                        event.stopPropagation()
                        deleteConversation(conversation.id)
                      }}
                    />,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<MessageOutlined className="text-blue-500 mt-1" />}
                    title={<span className="line-clamp-1">{conversation.title}</span>}
                    description={new Date(conversation.updated_at).toLocaleString()}
                  />
                </List.Item>
              )}
            />
          </div>
        </aside>

        <section className="bg-white border border-gray-200 rounded-lg flex flex-col overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <div className="font-semibold">{activeConversation?.title ?? '新对话'}</div>
            <Text type="secondary" className="text-xs">输入问题后会先检索你的知识库，再生成回答</Text>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50/60">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <Empty description="问一个和知识库相关的问题，开始第一次 RAG 对话" />
              </div>
            ) : (
              messages.map((item) => (
                <MessageBubble key={item.id} message={item} />
              ))
            )}
            <div ref={scrollRef} />
          </div>

          <div className="border-t border-gray-100 p-4">
            <Space.Compact className="w-full" size="large">
              <TextArea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onPressEnter={(event) => {
                  if (!event.shiftKey) {
                    event.preventDefault()
                    send()
                  }
                }}
                autoSize={{ minRows: 1, maxRows: 4 }}
                placeholder="例如：JWT 刷新机制怎么设计？"
                disabled={streaming}
              />
              <Button type="primary" icon={<SendOutlined />} loading={streaming} onClick={send}>
                发送
              </Button>
            </Space.Compact>
          </div>
        </section>
      </div>
    </div>
  )
}

function MessageBubble({ message: item }: { message: Message }) {
  const isUser = item.role === 'user'
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null)

  const handleFeedback = async (rating: string) => {
    if (!item.id || item.id.startsWith('local-')) return
    try {
      await evalApi.submitFeedback({ message_id: item.id, rating })
      setFeedbackGiven(rating)
    } catch {
      // 静默
    }
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[78%] rounded-lg border p-4 ${isUser ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-gray-200'}`}>
        {isUser ? (
          <div className="whitespace-pre-wrap">{item.content}</div>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {item.content || '正在思考...'}
            </ReactMarkdown>
          </div>
        )}
        {!isUser && item.sources && item.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <Text type="secondary" className="text-xs mr-2">来源</Text>
            {item.sources.map((source) => (
              <Tag key={source.note_id} color="blue">{source.title}</Tag>
            ))}
          </div>
        )}
        {!isUser && !item.id.startsWith('local-') && (
          <div className="mt-2 pt-2 border-t border-gray-100 flex gap-2">
            {feedbackGiven ? (
              <Text type="secondary" className="text-xs">
                {feedbackGiven === 'helpful' ? '感谢反馈' : '已收到反馈，会持续改进'}
              </Text>
            ) : (
              <>
                <Button
                  type="text"
                  size="small"
                  icon={<LikeOutlined />}
                  onClick={() => handleFeedback('helpful')}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<DislikeOutlined />}
                  onClick={() => handleFeedback('not_helpful')}
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
