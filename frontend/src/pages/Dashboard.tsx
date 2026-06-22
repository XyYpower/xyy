import { useEffect, useState } from 'react'
import { Button, Card, Empty, Input, Progress, Row, Col, Statistic, Typography, message } from 'antd'
import {
  ScheduleOutlined,
  TrophyOutlined,
  CheckCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ReviewStats } from '../api/review'
import { getDashboardData } from '../api/dashboard'
import type { InterviewSession } from '../api/interview'
import { noteApi } from '../api/notes'

const { Title, Text } = Typography

interface StreakData {
  lastReviewDate: string
  streakCount: number
}

function loadStreak(): StreakData {
  try {
    const raw = localStorage.getItem('knowbase_streak')
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { lastReviewDate: '', streakCount: 0 }
}

function saveStreak(data: StreakData) {
  localStorage.setItem('knowbase_streak', JSON.stringify(data))
}

function updateStreakOnReview(): number {
  const today = new Date().toISOString().slice(0, 10)
  const streak = loadStreak()

  if (streak.lastReviewDate === today) {
    return streak.streakCount
  }

  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const newCount = streak.lastReviewDate === yesterday ? streak.streakCount + 1 : 1
  saveStreak({ lastReviewDate: today, streakCount: newCount })
  return newCount
}

function getDisplayStreak(): number {
  const today = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const streak = loadStreak()

  if (streak.lastReviewDate === today || streak.lastReviewDate === yesterday) {
    return streak.streakCount
  }
  return 0
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<ReviewStats | null>(null)
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [streak, setStreak] = useState(0)
  const [quickTitle, setQuickTitle] = useState('')
  const [quickContent, setQuickContent] = useState('')
  const [quickAdding, setQuickAdding] = useState(false)

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const dashData = await getDashboardData()
        setStats(dashData.stats)
        setSessions(dashData.sessions.slice(0, 3))
      } catch {
        message.error('加载概览失败')
      }
    }
    fetchAll()
    setStreak(getDisplayStreak())
  }, [])

  const totalNotes = (stats?.mastered_count ?? 0) + (stats?.learning_count ?? 0) + (stats?.new_count ?? 0)
  const hasData = totalNotes > 0

  const handleStartReview = () => {
    updateStreakOnReview()
    navigate('/review')
  }

  const handleQuickAdd = async () => {
    const title = quickTitle.trim()
    if (!title) {
      message.warning('请输入标题')
      return
    }
    setQuickAdding(true)
    try {
      await noteApi.create({ title, content: quickContent.trim() })
      message.success('知识点已创建')
      setQuickTitle('')
      setQuickContent('')
      // 刷新统计数据
      const dashData = await getDashboardData()
      setStats(dashData.stats)
    } catch {
      message.error('创建失败')
    } finally {
      setQuickAdding(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* 顶部问候 */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="!mb-1">
            {streak > 0 ? `已连续学习 ${streak} 天` : '开始今天的学习'}
          </Title>
          <Text type="secondary">
            {hasData ? `共 ${totalNotes} 个知识点，已掌握 ${stats?.mastered_count ?? 0} 个` : '创建你的第一个知识点开始吧'}
          </Text>
        </div>
        {streak > 0 && (
          <div className="text-4xl" title="连续打卡天数">
            {streak >= 7 ? '🔥' : '📅'} {streak}
          </div>
        )}
      </div>

      {/* 快速添加 */}
      <Card className="mb-6" size="small">
        <div className="flex gap-2">
          <Input
            placeholder="快速添加知识点标题..."
            value={quickTitle}
            onChange={(e) => setQuickTitle(e.target.value)}
            onPressEnter={handleQuickAdd}
            className="flex-1"
          />
          <Input
            placeholder="内容（可选）"
            value={quickContent}
            onChange={(e) => setQuickContent(e.target.value)}
            onPressEnter={handleQuickAdd}
            className="flex-1"
          />
          <Button
            type="primary"
            icon={<PlusOutlined />}
            loading={quickAdding}
            onClick={handleQuickAdd}
          >
            添加
          </Button>
        </div>
      </Card>

      {!hasData && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg p-6 mb-6">
          <Title level={3} className="!text-white !mb-2">欢迎使用 KnowBase</Title>
          <p className="text-indigo-100 mb-4">用间隔复习巩固八股文记忆，用模拟面试检验掌握程度。</p>
          <div className="flex gap-3">
            <Button type="primary" ghost onClick={() => navigate('/notes')}>创建第一个知识点</Button>
            <Button type="primary" ghost onClick={() => navigate('/import')}>批量导入</Button>
          </div>
        </div>
      )}

      {/* 核心数据卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} md={8}>
          <Card
            hoverable
            onClick={handleStartReview}
            className={stats?.due_today ? 'border-indigo-300' : ''}
          >
            <Statistic
              title="今日待复习"
              value={stats?.due_today ?? 0}
              prefix={<ScheduleOutlined />}
              valueStyle={stats?.due_today ? { color: '#1677ff' } : undefined}
            />
            {stats?.due_today ? (
              <Button type="link" size="small" className="p-0 mt-2" onClick={handleStartReview}>
                开始复习 →
              </Button>
            ) : (
              <Text type="secondary" className="text-xs">今天已全部复习完</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="已掌握"
              value={stats?.mastered_count ?? 0}
              suffix={`/ ${totalNotes}`}
              prefix={<CheckCircleOutlined />}
            />
            <Progress
              percent={totalNotes ? Math.round(((stats?.mastered_count ?? 0) / totalNotes) * 100) : 0}
              showInfo={false}
              strokeColor="#52c41a"
              size="small"
              className="mt-2"
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card hoverable onClick={() => navigate('/interview')}>
            <Statistic title="面试次数" value={sessions.length} prefix={<TrophyOutlined />} />
            <Text type="secondary" className="text-xs">点击开始新一轮模拟面试</Text>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 学习进度 */}
        <Col xs={24} md={14}>
          <Card title="掌握进度">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>已掌握</span><span>{stats?.mastered_count ?? 0}</span>
                </div>
                <Progress
                  percent={totalNotes ? Math.round(((stats?.mastered_count ?? 0) / totalNotes) * 100) : 0}
                  showInfo={false}
                  strokeColor="#52c41a"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>学习中</span><span>{stats?.learning_count ?? 0}</span>
                </div>
                <Progress
                  percent={totalNotes ? Math.round(((stats?.learning_count ?? 0) / totalNotes) * 100) : 0}
                  showInfo={false}
                  strokeColor="#faad14"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>未学</span><span>{stats?.new_count ?? 0}</span>
                </div>
                <Progress
                  percent={totalNotes ? Math.round(((stats?.new_count ?? 0) / totalNotes) * 100) : 0}
                  showInfo={false}
                  strokeColor="#d9d9d9"
                />
              </div>
            </div>
          </Card>
        </Col>

        {/* 快捷入口 + 最近面试 */}
        <Col xs={24} md={10}>
          <Card title="快捷操作" className="mb-4">
            <div className="grid grid-cols-2 gap-2">
              <Button block onClick={() => navigate('/notes')}>知识点</Button>
              <Button block onClick={() => navigate('/import')}>导入知识</Button>
              <Button block onClick={handleStartReview}>开始复习</Button>
              <Button block onClick={() => navigate('/interview')}>模拟面试</Button>
              <Button block onClick={() => navigate('/chat')}>AI 对话</Button>
              <Button block onClick={() => navigate('/settings')}>设置</Button>
            </div>
          </Card>

          <Card title="最近面试">
            {sessions.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有面试记录" />
            ) : (
              <div className="space-y-2">
                {sessions.map((s) => (
                  <div
                    key={s.id}
                    className="flex justify-between items-center text-sm cursor-pointer hover:bg-gray-50 p-1 rounded"
                    onClick={() => navigate('/interview')}
                  >
                    <span className="truncate flex-1">{s.title}</span>
                    <span className={s.status === 'completed' ? 'text-green-600' : 'text-orange-500'}>
                      {s.status === 'completed' ? `${s.total_score ?? 0} 分` : '进行中'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
