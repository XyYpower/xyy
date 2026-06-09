import { useState, useEffect } from 'react'
import { Button, Card, Tag, Typography, Row, Col, Statistic, Space, Timeline, Empty, message } from 'antd'
import {
  TrophyOutlined,
  DownloadOutlined,
  ThunderboltOutlined,
  BookOutlined,
  ExperimentOutlined,
  RocketOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { portfolioApi, type PortfolioSummary, type ProjectReport, type LearningReport, type RecentRun } from '../api/portfolio'

const { Title, Text, Paragraph } = Typography

const runTypeLabels: Record<string, string> = {
  diagnosis: '诊断',
  plan: '规划',
  import_curate: '导入整理',
  daily_coach: '每日学习',
  interview: '面试',
  portfolio: '作品集',
}

export default function Portfolio() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [projectReport, setProjectReport] = useState<ProjectReport | null>(null)
  const [learningReport, setLearningReport] = useState<LearningReport | null>(null)
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([])
  const [loadingProject, setLoadingProject] = useState(false)
  const [loadingLearning, setLoadingLearning] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [summaryRes, runsRes] = await Promise.allSettled([
        portfolioApi.getSummary(),
        portfolioApi.getRecentRuns(),
      ])
      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value.data)
      if (runsRes.status === 'fulfilled') setRecentRuns(runsRes.value.data)
    } catch {
      // 静默
    }
  }

  const handleGenerateProject = async () => {
    setLoadingProject(true)
    try {
      const res = await portfolioApi.generateProjectReport()
      setProjectReport(res.data)
      message.success('项目报告已生成')
    } catch {
      message.error('生成失败')
    } finally {
      setLoadingProject(false)
    }
  }

  const handleGenerateLearning = async () => {
    setLoadingLearning(true)
    try {
      const res = await portfolioApi.generateLearningReport()
      setLearningReport(res.data)
      message.success('学习报告已生成')
    } catch {
      message.error('生成失败')
    } finally {
      setLoadingLearning(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Title level={2} className="!mb-1">
          <TrophyOutlined className="mr-2" />Portfolio
        </Title>
        <Text type="secondary">面向面试展示的项目报告和学习成果</Text>
      </div>

      {/* 数据总览 */}
      {summary && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col span={6}>
            <Card>
              <Statistic title="知识点" value={summary.notes_count} prefix={<BookOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="已掌握" value={summary.mastered_count} prefix={<TrophyOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="Agent 运行" value={summary.agent_runs} prefix={<ThunderboltOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="面试场次" value={summary.interview_sessions} prefix={<ExperimentOutlined />} />
            </Card>
          </Col>
        </Row>
      )}

      {/* 报告生成 */}
      <Row gutter={16} className="mb-6">
        <Col span={12}>
          <Card
            title={<><RocketOutlined /> 项目技术报告</>}
            extra={
              <Space>
                <Button size="small" loading={loadingProject} onClick={handleGenerateProject}>生成报告</Button>
                <Button size="small" icon={<DownloadOutlined />} onClick={() => portfolioApi.exportProjectMarkdown()}>导出 MD</Button>
              </Space>
            }
          >
            {projectReport ? (
              <div>
                <Paragraph strong>{projectReport.summary}</Paragraph>
                {projectReport.highlights.length > 0 && (
                  <div className="mt-3">
                    <Text type="secondary" className="text-sm">技术亮点：</Text>
                    <ul className="mt-1 text-sm">
                      {projectReport.highlights.map((h, i) => <li key={i}>{h}</li>)}
                    </ul>
                  </div>
                )}
                {projectReport.sections.length > 0 && (
                  <div className="mt-3">
                    {projectReport.sections.map((s, i) => (
                      <div key={i} className="mb-2">
                        <Text strong className="text-sm">{s.heading}</Text>
                        <div className="text-xs text-gray-500 mt-1 whitespace-pre-wrap">{s.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击生成项目技术报告" />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card
            title={<><BookOutlined /> 学习报告</>}
            extra={
              <Space>
                <Button size="small" loading={loadingLearning} onClick={handleGenerateLearning}>生成报告</Button>
                <Button size="small" icon={<DownloadOutlined />} onClick={() => portfolioApi.exportLearningMarkdown()}>导出 MD</Button>
              </Space>
            }
          >
            {learningReport ? (
              <div>
                <Paragraph strong>{learningReport.summary}</Paragraph>
                {learningReport.highlights.length > 0 && (
                  <div className="mt-3">
                    <Text type="secondary" className="text-sm">学习亮点：</Text>
                    <ul className="mt-1 text-sm">
                      {learningReport.highlights.map((h, i) => <li key={i}>{h}</li>)}
                    </ul>
                  </div>
                )}
                {learningReport.next_steps && learningReport.next_steps.length > 0 && (
                  <div className="mt-3">
                    <Text type="secondary" className="text-sm">下一步：</Text>
                    <ol className="mt-1 text-sm">
                      {learningReport.next_steps.map((s, i) => <li key={i}>{s}</li>)}
                    </ol>
                  </div>
                )}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击生成学习报告" />
            )}
          </Card>
        </Col>
      </Row>

      {/* Agent Run 回放 */}
      <Card
        title={<><ThunderboltOutlined /> 代表性 Agent Run</>}
        extra={<Button type="link" onClick={() => navigate('/traces')}>查看全部</Button>}
      >
        {recentRuns.length === 0 ? (
          <Empty description="暂无 Agent 运行记录" />
        ) : (
          <Timeline
            items={recentRuns.map((run) => ({
              color: run.status === 'completed' ? 'green' : run.status === 'failed' ? 'red' : 'blue',
              children: (
                <div>
                  <div className="flex items-center gap-2">
                    <Tag color="blue">{runTypeLabels[run.run_type] || run.run_type}</Tag>
                    <Tag color={run.status === 'completed' ? 'green' : run.status === 'failed' ? 'red' : 'default'}>
                      {run.status}
                    </Tag>
                    <Text type="secondary" className="text-xs">
                      {run.created_at ? new Date(run.created_at).toLocaleString() : '-'}
                    </Text>
                  </div>
                  {run.goal && <div className="text-sm mt-1">{run.goal}</div>}
                  <div className="text-xs text-gray-400 mt-1">
                    Token: {(run.total_prompt_tokens + run.total_completion_tokens).toLocaleString()}
                    {' | '}成本: ${run.estimated_cost.toFixed(4)}
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </div>
  )
}
