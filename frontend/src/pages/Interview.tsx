import { useEffect, useMemo, useState } from 'react'
import { Button, Empty, Input, List, Progress, Radio, Space, Tag, Typography, message } from 'antd'
import { CheckCircleOutlined, HistoryOutlined, PlayCircleOutlined, SendOutlined } from '@ant-design/icons'
import { interviewApi, type InterviewQuestion, type InterviewSession, type WeakPoint } from '../api/interview'

const { Text, Title } = Typography
const { TextArea } = Input

export default function Interview() {
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [weakPoints, setWeakPoints] = useState<WeakPoint[]>([])
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null)
  const [scope, setScope] = useState<'all' | 'weak_points'>('all')
  const [numQuestions, setNumQuestions] = useState(5)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [finishing, setFinishing] = useState(false)

  const currentQuestion = activeSession?.questions[currentIndex]
  const answeredCount = useMemo(
    () => activeSession?.questions.filter((question) => question.user_answer).length ?? 0,
    [activeSession],
  )
  const progressPercent = activeSession?.questions.length
    ? Math.round((answeredCount / activeSession.questions.length) * 100)
    : 0

  const fetchData = async () => {
    try {
      const [sessionsRes, weakRes] = await Promise.all([interviewApi.list(), interviewApi.weakPoints()])
      setSessions(sessionsRes.data)
      setWeakPoints(weakRes.data)
      if (!activeSession && sessionsRes.data.length > 0) {
        setActiveSession(sessionsRes.data[0])
      }
    } catch {
      message.error('加载面试数据失败')
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    setAnswer(currentQuestion?.user_answer ?? '')
  }, [currentQuestion?.id])

  const startInterview = async () => {
    setLoading(true)
    try {
      const response = await interviewApi.start({ scope, num_questions: numQuestions })
      setActiveSession(response.data)
      setSessions((current) => [response.data, ...current])
      setCurrentIndex(0)
      message.success('面试题已生成')
    } catch {
      message.error('开始面试失败')
    } finally {
      setLoading(false)
    }
  }

  const submitAnswer = async () => {
    if (!activeSession || !currentQuestion || !answer.trim()) {
      message.warning('请先填写回答')
      return
    }
    setSubmitting(true)
    try {
      const response = await interviewApi.submitAnswer(activeSession.id, currentQuestion.id, answer.trim())
      setActiveSession((current) => updateQuestion(current, response.data))
      message.success('AI 评分已生成')
    } catch {
      message.error('提交回答失败')
    } finally {
      setSubmitting(false)
    }
  }

  const finishInterview = async () => {
    if (!activeSession) return
    setFinishing(true)
    try {
      const response = await interviewApi.finish(activeSession.id)
      setActiveSession(response.data)
      setSessions((current) => current.map((item) => (item.id === response.data.id ? response.data : item)))
      await fetchData()
      message.success('面试已结束')
    } catch {
      message.error('结束面试失败')
    } finally {
      setFinishing(false)
    }
  }

  const selectSession = async (sessionId: string) => {
    try {
      const response = await interviewApi.get(sessionId)
      setActiveSession(response.data)
      setCurrentIndex(0)
    } catch {
      message.error('加载面试详情失败')
    }
  }

  return (
    <div>
      <div className="flex justify-between items-start mb-5">
        <div>
          <Title level={2} className="!mb-1">AI 模拟面试</Title>
          <Text type="secondary">基于你的知识点生成题目，逐题评分并沉淀薄弱点</Text>
        </div>
        <Space>
          <Radio.Group value={scope} onChange={(event) => setScope(event.target.value)}>
            <Radio.Button value="all">全部知识点</Radio.Button>
            <Radio.Button value="weak_points">薄弱优先</Radio.Button>
          </Radio.Group>
          <Radio.Group value={numQuestions} onChange={(event) => setNumQuestions(event.target.value)}>
            <Radio.Button value={3}>3 题</Radio.Button>
            <Radio.Button value={5}>5 题</Radio.Button>
            <Radio.Button value={8}>8 题</Radio.Button>
          </Radio.Group>
          <Button type="primary" icon={<PlayCircleOutlined />} loading={loading} onClick={startInterview}>
            开始面试
          </Button>
        </Space>
      </div>

      <div className="grid grid-cols-[280px_1fr] gap-4">
        <aside className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="px-4 py-3 border-b border-gray-100 font-medium flex items-center gap-2">
              <HistoryOutlined /> 面试历史
            </div>
            <List
              dataSource={sessions}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无面试" /> }}
              renderItem={(session) => (
                <List.Item
                  className={`!px-4 cursor-pointer ${activeSession?.id === session.id ? 'bg-blue-50' : ''}`}
                  onClick={() => selectSession(session.id)}
                >
                  <List.Item.Meta
                    title={<span className="line-clamp-1">{session.title}</span>}
                    description={
                      <Space direction="vertical" size={2}>
                        <Text type="secondary">{new Date(session.created_at).toLocaleString()}</Text>
                        <Tag color={session.status === 'completed' ? 'green' : 'gold'}>
                          {session.status === 'completed' ? `完成 ${session.total_score ?? 0} 分` : '进行中'}
                        </Tag>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="font-medium mb-3">薄弱知识点</div>
            {weakPoints.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无薄弱点" />
            ) : (
              <Space direction="vertical" className="w-full">
                {weakPoints.slice(0, 5).map((item) => (
                  <div key={item.note_id} className="flex justify-between gap-3 text-sm">
                    <span className="truncate">{item.title}</span>
                    <Tag color="red">{item.avg_score.toFixed(1)}</Tag>
                  </div>
                ))}
              </Space>
            )}
          </div>
        </aside>

        <main className="bg-white border border-gray-200 rounded-lg min-h-[620px]">
          {!activeSession ? (
            <div className="h-[620px] flex items-center justify-center">
              <Empty description="点击开始面试，生成第一轮题目" />
            </div>
          ) : activeSession.status === 'completed' ? (
            <ResultView session={activeSession} />
          ) : (
            <div className="p-6">
              <div className="flex justify-between items-start mb-5">
                <div>
                  <Text type="secondary">第 {currentIndex + 1} / {activeSession.questions.length} 题</Text>
                  <Title level={4} className="!mt-1 !mb-0">{currentQuestion?.question}</Title>
                </div>
                <Tag color="blue">{activeSession.scope === 'weak_points' ? '薄弱优先' : '全部知识点'}</Tag>
              </div>

              <Progress percent={progressPercent} className="mb-5" />

              <TextArea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                rows={10}
                placeholder="先讲核心概念，再展开项目场景、常见坑和权衡..."
              />

              {currentQuestion?.ai_feedback && (
                <div className="mt-4 border border-blue-100 bg-blue-50 rounded-lg p-4">
                  <Space className="mb-2">
                    <Tag color="blue">{currentQuestion.ai_score}/10</Tag>
                    <Text strong>AI 反馈</Text>
                  </Space>
                  <div className="text-gray-700 whitespace-pre-wrap">{currentQuestion.ai_feedback}</div>
                </div>
              )}

              <div className="mt-5 flex justify-between">
                <Space>
                  <Button disabled={currentIndex === 0} onClick={() => setCurrentIndex((index) => index - 1)}>
                    上一题
                  </Button>
                  <Button
                    disabled={currentIndex + 1 >= activeSession.questions.length}
                    onClick={() => setCurrentIndex((index) => index + 1)}
                  >
                    下一题
                  </Button>
                </Space>
                <Space>
                  <Button type="primary" icon={<SendOutlined />} loading={submitting} onClick={submitAnswer}>
                    提交答案
                  </Button>
                  <Button
                    icon={<CheckCircleOutlined />}
                    disabled={answeredCount === 0}
                    loading={finishing}
                    onClick={finishInterview}
                  >
                    结束面试
                  </Button>
                </Space>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

function updateQuestion(session: InterviewSession | null, question: InterviewQuestion): InterviewSession | null {
  if (!session) return session
  return {
    ...session,
    questions: session.questions.map((item) => (item.id === question.id ? question : item)),
  }
}

function ResultView({ session }: { session: InterviewSession }) {
  const maxScore = session.questions.length * 10
  const percent = maxScore ? Math.round(((session.total_score ?? 0) / maxScore) * 100) : 0

  return (
    <div className="p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={3} className="!mb-1">面试结果</Title>
          <Text type="secondary">{session.title}</Text>
        </div>
        <div className="text-right">
          <div className="text-4xl font-semibold">{session.total_score ?? 0}/{maxScore}</div>
          <Text type="secondary">总分</Text>
        </div>
      </div>

      <Progress percent={percent} className="mb-6" />

      {session.summary && (
        <div className="border border-green-100 bg-green-50 rounded-lg p-4 mb-5">
          <Text strong>AI 总结</Text>
          <div className="mt-2 whitespace-pre-wrap text-gray-700">{session.summary}</div>
        </div>
      )}

      <List
        dataSource={session.questions}
        renderItem={(question) => (
          <List.Item className="!px-0">
            <div className="w-full border border-gray-100 rounded-lg p-4">
              <div className="flex justify-between gap-3">
                <Text strong>Q{question.question_order}. {question.question}</Text>
                <Tag color={(question.ai_score ?? 0) >= 7 ? 'green' : 'orange'}>{question.ai_score ?? '-'} / 10</Tag>
              </div>
              <div className="mt-3 text-gray-600 whitespace-pre-wrap">{question.user_answer || '未作答'}</div>
              {question.ai_feedback && (
                <div className="mt-3 text-gray-700 bg-gray-50 rounded-md p-3">{question.ai_feedback}</div>
              )}
            </div>
          </List.Item>
        )}
      />
    </div>
  )
}
