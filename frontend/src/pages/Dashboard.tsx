import { useEffect, useState } from 'react'
import { Button, Card, Empty, Progress, Row, Col, Statistic, Tag, Typography, List, message } from 'antd'
import {
  BookOutlined,
  ScheduleOutlined,
  TrophyOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ReviewStats } from '../api/review'
import { getDashboardData } from '../api/dashboard'
import type { InterviewSession } from '../api/interview'
import type { TraceStats } from '../api/traces'
import { workspaceApi, type LearningTask } from '../api/workspace'

const { Title, Text } = Typography

const taskTypeIcons: Record<string, React.ReactNode> = {
  learn: <BookOutlined />,
  review: <ScheduleOutlined />,
  interview: <TrophyOutlined />,
}

const taskTypeColors: Record<string, string> = {
  learn: 'blue',
  review: 'orange',
  interview: 'purple',
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<ReviewStats | null>(null)
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [traceStats, setTraceStats] = useState<TraceStats | null>(null)
  const [todayTasks, setTodayTasks] = useState<LearningTask[]>([])

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [dashData, tasksRes] = await Promise.allSettled([
          getDashboardData(),
          workspaceApi.getTodayTasks(),
        ])
        if (dashData.status === 'fulfilled') {
          setStats(dashData.value.stats)
          setSessions(dashData.value.sessions.slice(0, 3))
          setTraceStats(dashData.value.traceStats)
        }
        if (tasksRes.status === 'fulfilled') {
          setTodayTasks(tasksRes.value.data.tasks)
        }
      } catch {
        message.error('加载概览失败')
      }
    }
    fetchAll()
  }, [])

  const totalNotes = (stats?.mastered_count ?? 0) + (stats?.learning_count ?? 0) + (stats?.new_count ?? 0)
  const hasData = totalNotes > 0

  const handleCompleteTask = async (taskId: string) => {
    try {
      await workspaceApi.completeTask(taskId)
      setTodayTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: 'completed' } : t))
    } catch {
      // 静默
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="!mb-1">今日学习工作台</Title>
          <Text type="secondary">今天该做什么，一目了然</Text>
        </div>
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => navigate('/workspace')}>
          Agent 工作台
        </Button>
      </div>

      {/* 新用户引导 */}
      {!hasData && (
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg p-6 mb-6">
          <Title level={3} className="!text-white !mb-2">欢迎使用 KnowBase</Title>
          <p className="text-indigo-100 mb-4">开始构建你的编程知识库，AI 会帮你规划学习路径、生成复习卡片和模拟面试。</p>
          <div className="flex gap-3">
            <Button type="primary" ghost onClick={() => navigate('/notes')}>创建第一个知识点</Button>
            <Button type="primary" ghost onClick={() => navigate('/import')}>导入知识内容</Button>
            <Button type="primary" ghost onClick={() => navigate('/workspace')}>使用 Agent 规划</Button>
          </div>
        </div>
      )}

      {/* 今日状态速览 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col span={6}>
          <Card hoverable onClick={() => navigate('/review')}>
            <Statistic title="今日待复习" value={stats?.due_today ?? 0} prefix={<ScheduleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable onClick={() => navigate('/workspace')}>
            <Statistic title="待完成任务" value={todayTasks.filter(t => t.status !== 'completed').length} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已掌握" value={stats?.mastered_count ?? 0} suffix={`/ ${totalNotes}`} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card hoverable onClick={() => navigate('/traces')}>
            <Statistic title="Agent 运行" value={traceStats?.total_runs ?? 0} prefix={<ThunderboltOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 主区域 */}
      <Row gutter={[16, 16]}>
        {/* 左侧：今日任务队列 */}
        <Col span={14}>
          <Card
            title="今日任务队列"
            extra={<Button type="link" onClick={() => navigate('/workspace')}>查看全部</Button>}
          >
            {todayTasks.length === 0 ? (
              <Empty description="暂无今日任务">
                <Button type="primary" icon={<RocketOutlined />} onClick={() => navigate('/workspace')}>
                  运行 Agent 规划
                </Button>
              </Empty>
            ) : (
              <List
                dataSource={todayTasks.slice(0, 8)}
                renderItem={(task) => (
                  <List.Item
                    actions={
                      task.status === 'completed'
                        ? [<Tag key="done" color="green">已完成</Tag>]
                        : [
                            <Button key="done" type="link" size="small" onClick={() => handleCompleteTask(task.id)}>
                              完成
                            </Button>,
                          ]
                    }
                  >
                    <List.Item.Meta
                      avatar={taskTypeIcons[task.task_type] || <BookOutlined />}
                      title={
                        <span className={task.status === 'completed' ? 'line-through text-gray-400' : ''}>
                          {task.title}
                        </span>
                      }
                      description={
                        <Tag color={taskTypeColors[task.task_type] || 'default'}>
                          {task.task_type === 'learn' ? '学习' : task.task_type === 'review' ? '复习' : task.task_type}
                        </Tag>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>

          {/* 掌握度分布 */}
          <Card title="学习进度" className="mt-4">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>已掌握</span><span>{stats?.mastered_count ?? 0}</span>
                </div>
                <Progress percent={totalNotes ? Math.round(((stats?.mastered_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} strokeColor="#52c41a" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>学习中</span><span>{stats?.learning_count ?? 0}</span>
                </div>
                <Progress percent={totalNotes ? Math.round(((stats?.learning_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} strokeColor="#faad14" />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>未学</span><span>{stats?.new_count ?? 0}</span>
                </div>
                <Progress percent={totalNotes ? Math.round(((stats?.new_count ?? 0) / totalNotes) * 100) : 0} showInfo={false} strokeColor="#d9d9d9" />
              </div>
            </div>
          </Card>
        </Col>

        {/* 右侧：快捷入口 + 面试 + AI 概览 */}
        <Col span={10}>
          {/* 快捷操作 */}
          <Card title="快捷操作" className="mb-4">
            <div className="grid grid-cols-2 gap-2">
              <Button block onClick={() => navigate('/notes')}>知识点</Button>
              <Button block onClick={() => navigate('/import')}>导入知识</Button>
              <Button block onClick={() => navigate('/review')}>开始复习</Button>
              <Button block onClick={() => navigate('/interview')}>模拟面试</Button>
              <Button block onClick={() => navigate('/chat')}>AI 对话</Button>
              <Button block onClick={() => navigate('/paths')}>学习路径</Button>
            </div>
          </Card>

          {/* 最近面试 */}
          <Card
            title="最近面试"
            extra={<Button type="link" onClick={() => navigate('/interview')}>全部</Button>}
            className="mb-4"
          >
            {sessions.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有面试记录" />
            ) : (
              <div className="space-y-2">
                {sessions.map((s) => (
                  <div key={s.id} className="flex justify-between items-center text-sm">
                    <span className="truncate flex-1">{s.title}</span>
                    <Tag color={s.status === 'completed' ? 'green' : 'gold'}>
                      {s.status === 'completed' ? `${s.total_score ?? 0} 分` : '进行中'}
                    </Tag>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* AI 使用概览 */}
          <Card
            title="AI 使用概览"
            extra={<Button type="link" onClick={() => navigate('/traces')}>Trace Lab</Button>}
          >
            {traceStats ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Agent 运行</span>
                  <span className="font-medium">{traceStats.total_runs}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">AI 调用</span>
                  <span className="font-medium">{traceStats.total_ai_calls}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">成功率</span>
                  <span className="font-medium">{traceStats.success_rate}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Token 消耗</span>
                  <span className="font-medium">{(traceStats.total_prompt_tokens + traceStats.total_completion_tokens).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">预估成本</span>
                  <span className="font-medium">${traceStats.total_cost.toFixed(4)}</span>
                </div>
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
