import { useState, useEffect } from 'react'
import { Button, Input, Card, Tag, Typography, List, message, Spin, Empty } from 'antd'
import {
  ThunderboltOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  AimOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { workspaceApi, type DiagnosisResult, type PlanResult, type LearningTask } from '../api/workspace'

const { Title, Text, Paragraph } = Typography

const taskTypeLabels: Record<string, string> = {
  learn: '学习',
  review: '复习',
  practice: '练习',
  interview: '面试',
}

const taskTypeColors: Record<string, string> = {
  learn: 'blue',
  review: 'orange',
  practice: 'green',
  interview: 'purple',
}

export default function AgentWorkspace() {
  const navigate = useNavigate()
  const [goal, setGoal] = useState('')
  const [running, setRunning] = useState(false)
  const [diagnosis, setDiagnosis] = useState<DiagnosisResult | null>(null)
  const [plan, setPlan] = useState<PlanResult | null>(null)
  const [todayTasks, setTodayTasks] = useState<LearningTask[]>([])
  const [loadingTasks, setLoadingTasks] = useState(false)

  useEffect(() => {
    fetchTodayTasks()
  }, [])

  const fetchTodayTasks = async () => {
    setLoadingTasks(true)
    try {
      const res = await workspaceApi.getTodayTasks()
      setTodayTasks(res.data.tasks)
    } catch {
      // 静默
    } finally {
      setLoadingTasks(false)
    }
  }

  const handleRun = async () => {
    if (!goal.trim()) {
      message.warning('请输入学习目标')
      return
    }
    setRunning(true)
    setDiagnosis(null)
    setPlan(null)
    try {
      const res = await workspaceApi.diagnoseAndPlan(goal.trim())
      setDiagnosis(res.data.diagnosis)
      setPlan(res.data.plan)
      message.success('诊断和规划完成')
      fetchTodayTasks()
    } catch {
      message.error('运行失败，请重试')
    } finally {
      setRunning(false)
    }
  }

  const handleCompleteTask = async (taskId: string) => {
    try {
      await workspaceApi.completeTask(taskId)
      setTodayTasks(todayTasks.map(t => t.id === taskId ? { ...t, status: 'completed' } : t))
      message.success('任务已完成')
    } catch {
      message.error('操作失败')
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Title level={2} className="!mb-1">
          <ThunderboltOutlined className="mr-2" />Agent Workspace
        </Title>
        <Text type="secondary">输入学习目标，Agent 会诊断薄弱点并生成可执行计划</Text>
      </div>

      {/* 输入区 */}
      <Card className="mb-6">
        <div className="flex gap-3">
          <Input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onPressEnter={handleRun}
            placeholder="例如：3 个月后面试 AI Agent 应用开发岗位"
            size="large"
            className="flex-1"
          />
          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            loading={running}
            onClick={handleRun}
          >
            开始诊断 + 规划
          </Button>
        </div>
      </Card>

      {/* 诊断结果 */}
      {diagnosis && (
        <Card className="mb-4" title={<><AimOutlined /> 诊断结果</>}>
          <Paragraph>{diagnosis.summary}</Paragraph>
          {diagnosis.weak_areas.length > 0 && (
            <div className="space-y-3 mt-3">
              {diagnosis.weak_areas.map((area, i) => (
                <div key={i} className="border border-gray-100 rounded-md p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Tag color="red">P{area.priority}</Tag>
                    <Text strong>{area.area}</Text>
                  </div>
                  <Text type="secondary" className="text-sm">{area.reason}</Text>
                  {area.suggested_topics.length > 0 && (
                    <div className="mt-2 flex gap-1 flex-wrap">
                      {area.suggested_topics.map((t, j) => <Tag key={j} color="blue">{t}</Tag>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {diagnosis.next_steps.length > 0 && (
            <div className="mt-3">
              <Text type="secondary" className="text-sm">建议步骤：</Text>
              <ol className="mt-1 text-sm text-gray-600">
                {diagnosis.next_steps.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
          )}
        </Card>
      )}

      {/* 规划结果 */}
      {plan && (
        <Card className="mb-4" title={<><RocketOutlined /> 学习计划</>}>
          <div className="mb-3">
            <Text strong className="text-lg">{plan.name}</Text>
            <div className="text-gray-500 mt-1">{plan.description}</div>
          </div>
          <div className="flex gap-4 mb-3">
            <Tag color="blue">{plan.modules_count} 个模块</Tag>
            <Tag color="green">{plan.tasks_count} 个任务</Tag>
          </div>
          {plan.tasks.length > 0 && (
            <div className="space-y-2">
              {plan.tasks.map((task, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <ClockCircleOutlined className="text-gray-400" />
                  <span>{task.title}</span>
                  <Tag color={taskTypeColors[task.task_type] || 'default'} className="ml-auto">
                    {taskTypeLabels[task.task_type] || task.task_type}
                  </Tag>
                  {task.due_at && (
                    <Text type="secondary" className="text-xs">
                      {new Date(task.due_at).toLocaleDateString()}
                    </Text>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="mt-3">
            <Button type="link" onClick={() => navigate('/paths')}>查看完整学习路径</Button>
          </div>
        </Card>
      )}

      {/* 今日任务 */}
      <Card
        title={<><ClockCircleOutlined /> 今日学习任务</>}
        extra={<Button type="link" onClick={() => navigate('/review')}>去复习</Button>}
      >
        {loadingTasks ? (
          <div className="text-center p-4"><Spin /></div>
        ) : todayTasks.length === 0 ? (
          <Empty description="今日暂无学习任务，试试上面的诊断功能" />
        ) : (
          <List
            dataSource={todayTasks}
            renderItem={(task) => (
              <List.Item
                actions={
                  task.status !== 'completed'
                    ? [<Button type="link" onClick={() => handleCompleteTask(task.id)}>完成</Button>]
                    : [<Tag color="green">已完成</Tag>]
                }
              >
                <List.Item.Meta
                  title={
                    <span className={task.status === 'completed' ? 'line-through text-gray-400' : ''}>
                      {task.title}
                    </span>
                  }
                  description={
                    <div className="flex gap-2">
                      <Tag color={taskTypeColors[task.task_type] || 'default'}>
                        {taskTypeLabels[task.task_type] || task.task_type}
                      </Tag>
                      {task.topic_title && <Text type="secondary" className="text-xs">{task.topic_title}</Text>}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
