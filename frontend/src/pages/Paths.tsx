import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Collapse, Empty, Input, List, Space, Tag, Typography, message } from 'antd'
import { BranchesOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { pathsApi, type LearningPath } from '../api/paths'

const { Text, Title } = Typography

export default function Paths() {
  const [goal, setGoal] = useState('后端面试')
  const [paths, setPaths] = useState<LearningPath[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  const selectedPath = useMemo(
    () => paths.find((path) => path.id === selectedId) ?? paths[0] ?? null,
    [paths, selectedId]
  )

  const loadPaths = async () => {
    setLoading(true)
    try {
      const response = await pathsApi.list()
      setPaths(response.data)
      setSelectedId((current) => current ?? response.data[0]?.id ?? null)
    } catch {
      message.error('加载学习路径失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPaths()
  }, [])

  const generatePath = async () => {
    const trimmed = goal.trim()
    if (trimmed.length < 2) {
      message.warning('目标至少 2 个字符')
      return
    }
    setGenerating(true)
    try {
      const response = await pathsApi.generate(trimmed)
      setPaths((current) => [response.data, ...current])
      setSelectedId(response.data.id)
      message.success('学习路径已生成')
    } catch {
      message.error('生成学习路径失败')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 mb-6">
        <div>
          <Title level={2} className="!mb-1">学习路径</Title>
          <Text type="secondary">把一个目标拆成可执行的知识模块</Text>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={loadPaths}>
          刷新
        </Button>
      </div>

      <Card className="mb-5">
        <Space.Compact className="w-full">
          <Input
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            onPressEnter={generatePath}
            placeholder="例如：3 个月后面试后端开发"
          />
          <Button type="primary" icon={<PlusOutlined />} loading={generating} onClick={generatePath}>
            生成路径
          </Button>
        </Space.Compact>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
        <Card title="我的路径" className="h-fit">
          {paths.length === 0 ? (
            <Empty description="还没有学习路径" />
          ) : (
            <List
              loading={loading}
              dataSource={paths}
              renderItem={(path) => (
                <List.Item
                  key={path.id}
                  className={`cursor-pointer rounded-md !px-3 ${
                    selectedPath?.id === path.id ? 'bg-indigo-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedId(path.id)}
                >
                  <List.Item.Meta
                    avatar={<BranchesOutlined className="text-indigo-500 mt-1" />}
                    title={<span className="line-clamp-1">{path.name}</span>}
                    description={`${path.modules.length} 个模块`}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        <Card>
          {!selectedPath ? (
            <Empty description="生成或选择一个学习路径" />
          ) : (
            <>
              <div className="mb-5">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <Title level={3} className="!m-0">{selectedPath.name}</Title>
                  <Tag color="blue">{selectedPath.modules.length} 个模块</Tag>
                </div>
                <Text type="secondary">{selectedPath.description}</Text>
              </div>

              <Collapse
                key={selectedPath.id}
                defaultActiveKey={selectedPath.modules.slice(0, 2).map((module, index) => `${index}-${module.priority}`)}
                items={selectedPath.modules.map((module, index) => ({
                  key: `${index}-${module.priority}`,
                  label: (
                    <div className="flex items-center justify-between gap-3">
                      <span>{module.name}</span>
                      <Tag>优先级 {module.priority}</Tag>
                    </div>
                  ),
                  children: (
                    <div className="flex flex-wrap gap-2">
                      {module.topics.map((topic) => (
                        <Tag key={topic} color="geekblue">{topic}</Tag>
                      ))}
                    </div>
                  ),
                }))}
              />
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
