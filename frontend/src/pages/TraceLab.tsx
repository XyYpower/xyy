import { useState, useEffect } from 'react'
import { Card, Table, Tag, Typography, Statistic, Row, Col, Drawer, Timeline, Descriptions, Empty, Spin, message } from 'antd'
import { ThunderboltOutlined, CheckCircleOutlined, ClockCircleOutlined, DollarOutlined } from '@ant-design/icons'
import { traceApi, type AgentRun, type AgentRunDetail, type TraceStats } from '../api/traces'

const { Title, Text } = Typography

const statusColors: Record<string, string> = {
  queued: 'default',
  running: 'processing',
  waiting_approval: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
}

const runTypeLabels: Record<string, string> = {
  diagnosis: '诊断',
  plan: '规划',
  import_curate: '导入整理',
  daily_coach: '每日学习',
  interview: '面试',
  portfolio: '作品集',
}

export default function TraceLab() {
  const [stats, setStats] = useState<TraceStats | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [selectedRun, setSelectedRun] = useState<AgentRunDetail | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    fetchRuns()
  }, [page])

  const fetchStats = async () => {
    try {
      const res = await traceApi.getStats()
      setStats(res.data)
    } catch {
      // 静默失败
    }
  }

  const fetchRuns = async () => {
    setLoading(true)
    try {
      const res = await traceApi.listRuns({ page, page_size: 15 })
      setRuns(res.data.items)
      setTotal(res.data.total)
    } catch {
      message.error('加载运行记录失败')
    } finally {
      setLoading(false)
    }
  }

  const openDetail = async (id: string) => {
    setDetailLoading(true)
    setDrawerOpen(true)
    try {
      const res = await traceApi.getRunDetail(id)
      setSelectedRun(res.data)
    } catch {
      message.error('加载详情失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const columns = [
    {
      title: '类型',
      dataIndex: 'run_type',
      key: 'run_type',
      width: 100,
      render: (t: string) => runTypeLabels[t] || t,
    },
    {
      title: '目标',
      dataIndex: 'goal',
      key: 'goal',
      ellipsis: true,
      render: (g: string | null) => g || <Text type="secondary">-</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    {
      title: 'Token',
      key: 'tokens',
      width: 130,
      render: (_: unknown, r: AgentRun) => (
        <Text type="secondary">{(r.total_prompt_tokens + r.total_completion_tokens).toLocaleString()}</Text>
      ),
    },
    {
      title: '成本',
      dataIndex: 'estimated_cost',
      key: 'cost',
      width: 80,
      render: (c: number) => `$${c.toFixed(4)}`,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (t: string | null) => t ? new Date(t).toLocaleString() : '-',
    },
  ]

  return (
    <div className="max-w-6xl mx-auto">
      <Title level={2} className="!mb-1">Trace Lab</Title>
      <Text type="secondary">Agent 运行追踪与 AI 调用监控</Text>

      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} className="mt-4 mb-6">
          <Col span={6}>
            <Card>
              <Statistic title="总运行次数" value={stats.total_runs} prefix={<ThunderboltOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="成功率" value={stats.success_rate} suffix="%" prefix={<CheckCircleOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="总 Token" value={stats.total_prompt_tokens + stats.total_completion_tokens} prefix={<ClockCircleOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="总成本" value={stats.total_cost} precision={4} prefix={<DollarOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      {/* 运行列表 */}
      <Card title="Agent 运行记录">
        <Table
          dataSource={runs}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: 15,
            total,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onRow={(record) => ({
            onClick: () => openDetail(record.id),
            style: { cursor: 'pointer' },
          })}
          locale={{ emptyText: <Empty description="暂无 Agent 运行记录" /> }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="运行详情"
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelectedRun(null) }}
        width={640}
      >
        {detailLoading ? (
          <div className="text-center p-8"><Spin /></div>
        ) : selectedRun ? (
          <div className="space-y-4">
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="类型">{runTypeLabels[selectedRun.run_type] || selectedRun.run_type}</Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusColors[selectedRun.status]}>{selectedRun.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="目标" span={2}>{selectedRun.goal || '-'}</Descriptions.Item>
              <Descriptions.Item label="Token">{selectedRun.total_prompt_tokens + selectedRun.total_completion_tokens}</Descriptions.Item>
              <Descriptions.Item label="成本">${selectedRun.estimated_cost.toFixed(4)}</Descriptions.Item>
            </Descriptions>

            {selectedRun.steps.length > 0 && (
              <Card title="执行步骤" size="small">
                <Timeline
                  items={selectedRun.steps.map((s) => ({
                    color: s.status === 'completed' ? 'green' : s.status === 'failed' ? 'red' : 'blue',
                    children: (
                      <div>
                        <Text strong>{s.node_name}</Text>
                        <Text type="secondary" className="ml-2">({s.agent_name})</Text>
                        <br />
                        <Tag color={statusColors[s.status] || 'default'} className="mt-1">{s.status}</Tag>
                        {s.latency_ms !== null && <Text type="secondary" className="ml-2">{s.latency_ms}ms</Text>}
                        {s.reasoning_summary && <div className="mt-1 text-gray-500 text-xs">{s.reasoning_summary}</div>}
                        {s.error_message && <div className="mt-1 text-red-500 text-xs">{s.error_message}</div>}
                      </div>
                    ),
                  }))}
                />
              </Card>
            )}

            {selectedRun.tool_calls.length > 0 && (
              <Card title="工具调用" size="small">
                <Table
                  dataSource={selectedRun.tool_calls}
                  rowKey="id"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '工具', dataIndex: 'tool_name', key: 'tool_name', width: 150 },
                    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (s: string) => <Tag color={s === 'success' ? 'green' : 'red'}>{s}</Tag> },
                    { title: '耗时', dataIndex: 'latency_ms', key: 'latency_ms', width: 80, render: (ms: number | null) => ms !== null ? `${ms}ms` : '-' },
                    { title: '错误', dataIndex: 'error_message', key: 'error_message', ellipsis: true },
                  ]}
                />
              </Card>
            )}

            {selectedRun.error_message && (
              <Card title="错误信息" size="small">
                <Text type="danger">{selectedRun.error_message}</Text>
              </Card>
            )}
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}
