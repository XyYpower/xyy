import { useEffect, useMemo, useState } from 'react'
import { Button, Empty, Progress, Tag, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { noteApi, type Note } from '../api/notes'
import { reviewApi, type ReviewStats } from '../api/review'

const { Title, Text } = Typography

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<ReviewStats | null>(null)
  const [notes, setNotes] = useState<Note[]>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, notesRes] = await Promise.all([
          reviewApi.getStats(),
          noteApi.list({ page: 1, page_size: 5 }),
        ])
        setStats(statsRes.data)
        setNotes(notesRes.data.items)
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
      </div>
    </div>
  )
}

