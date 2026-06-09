import { useEffect, useMemo, useState } from 'react'
import { Button, Empty, Progress, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import type { Note } from '../api/notes'
import type { ReviewStats } from '../api/review'
import { getDashboardData } from '../api/dashboard'
import type { InterviewSession } from '../api/interview'
import type { TraceStats } from '../api/traces'

const { Title, Text } = Typography

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<ReviewStats | null>(null)
  const [notes, setNotes] = useState<Note[]>([])
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [traceStats, setTraceStats] = useState<TraceStats | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getDashboardData()
        setStats(data.stats)
        setNotes(data.notes)
        setSessions(data.sessions.slice(0, 3))
        setTraceStats(data.traceStats)
      } catch {
        message.error('加载概览失败')
      }
    }
    fetchData()
  }, [])

  const totalNotes = useMemo(
    () => (stats?.mastered_count ?? 0) + (stats?.learning_count ?? 0) + (stats?.new_count ?? 0),
    [stats],
  )
  const masteredPercent = totalNotes ? Math.round(((stats?.mastered_count ?? 0) / totalNotes) * 100) : 0
  const chartData = useMemo(
    () => [
      stats?.new_count ?? 0,
      stats?.learning_count ?? 0,
      stats?.mastered_count ?? 0,
      stats?.due_today ?? 0,
      sessions.length,
      sessions.filter((session) => session.status === 'completed').length,
      stats?.total_cards ?? 0,
    ],
    [sessions, stats],
  )
  const chartMax = Math.max(...chartData, 1)

  return (
    <div>
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="!mb-1">学习概览</Title>
          <Text type="secondary">关注今天该复习什么，以及知识点掌握进度</Text>
        </div>
        <Button type="primary" onClick={() => navigate('/review')}>开始复习</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-500">今日待复习</div>
          <div className="text-4xl font-semibold mt-2">{stats?.due_today ?? 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-500">全部复习卡片</div>
          <div className="text-4xl font-semibold mt-2">{stats?.total_cards ?? 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="text-sm text-gray-500">掌握进度</div>
          <Progress percent={masteredPercent} className="mt-4" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>掌握度分布</Title>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1"><span>已掌握</span><span>{stats?.mastered_count ?? 0}</span></div>
              <Progress percent={totalNotes ? Math.round(((stats?.mastered_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1"><span>学习中</span><span>{stats?.learning_count ?? 0}</span></div>
              <Progress percent={totalNotes ? Math.round(((stats?.learning_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} strokeColor="#faad14" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1"><span>未学</span><span>{stats?.new_count ?? 0}</span></div>
              <Progress percent={totalNotes ? Math.round(((stats?.new_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} strokeColor="#8c8c8c" />
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>学习曲线</Title>
          <div className="h-44 flex items-end gap-3 border-b border-gray-100 pb-3">
            {chartData.map((value, index) => (
              <div key={index} className="flex-1 flex flex-col items-center gap-2">
                <div
                  className="w-full rounded-t bg-blue-500/80 min-h-2"
                  style={{ height: `${Math.max(8, (value / chartMax) * 140)}px` }}
                />
                <span className="text-xs text-gray-500">{value}</span>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 text-xs text-gray-500 mt-2 text-center">
            {['未学', '学习', '掌握', '待复习', '面试', '完成', '卡片'].map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>最近知识点</Title>
          {notes.length === 0 ? (
            <Empty description="还没有知识点" />
          ) : (
            <div className="space-y-3">
              {notes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => navigate(`/notes/${note.id}`)}
                  className="w-full text-left border border-gray-100 rounded-md p-3 hover:border-indigo-300"
                >
                  <div className="font-medium">{note.title}</div>
                  <div className="mt-2">
                    <Tag>{note.source_type}</Tag>
                    <Tag color={note.mastery_level === 2 ? 'green' : note.mastery_level === 1 ? 'gold' : 'default'}>
                      {note.mastery_level === 2 ? '已掌握' : note.mastery_level === 1 ? '学习中' : '未学'}
                    </Tag>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <Title level={4} className="!mb-0">面试历史</Title>
            <Button type="link" onClick={() => navigate('/interview')}>去面试</Button>
          </div>
          {sessions.length === 0 ? (
            <Empty description="还没有面试记录" />
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => navigate('/interview')}
                  className="w-full text-left border border-gray-100 rounded-md p-3 hover:border-blue-300"
                >
                  <div className="flex justify-between gap-3">
                    <div className="font-medium truncate">{session.title}</div>
                    <Tag color={session.status === 'completed' ? 'green' : 'gold'}>
                      {session.status === 'completed' ? `${session.total_score ?? 0} 分` : '进行中'}
                    </Tag>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {new Date(session.created_at).toLocaleString()}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <Title level={4} className="!mb-0">AI 使用概览</Title>
            <Button type="link" onClick={() => navigate('/traces')}>Trace Lab</Button>
          </div>
          {traceStats ? (
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Agent 运行次数</span>
                <span className="font-medium">{traceStats.total_runs}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">AI 调用次数</span>
                <span className="font-medium">{traceStats.total_ai_calls}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">成功率</span>
                <span className="font-medium">{traceStats.success_rate}%</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">总 Token 消耗</span>
                <span className="font-medium">{(traceStats.total_prompt_tokens + traceStats.total_completion_tokens).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">预估成本</span>
                <span className="font-medium">${traceStats.total_cost.toFixed(4)}</span>
              </div>
            </div>
          ) : (
            <Empty description="暂无 AI 使用数据" />
          )}
        </div>
      </div>
    </div>
  )
}
