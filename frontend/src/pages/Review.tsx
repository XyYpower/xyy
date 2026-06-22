import { useEffect, useMemo, useState } from 'react'
import { Button, Empty, Progress, Space, Tag, Typography, message } from 'antd'
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons'
import { reviewApi, type ReviewCard, type ReviewStats } from '../api/review'

const { Title, Text } = Typography

const cardTypeLabel: Record<ReviewCard['card_type'], string> = {
  concept: '概念',
  code: '代码',
  scenario: '场景',
}

export default function Review() {
  const [cards, setCards] = useState<ReviewCard[]>([])
  const [stats, setStats] = useState<ReviewStats | null>(null)
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [loading, setLoading] = useState(false)
  const [startTime, setStartTime] = useState<number>(Date.now())

  const current = cards[index]
  const completed = useMemo(() => Math.min(index, cards.length), [index, cards.length])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [todayRes, statsRes] = await Promise.all([reviewApi.getToday(), reviewApi.getStats()])
      setCards(todayRes.data)
      setStats(statsRes.data)
      setIndex(0)
      setFlipped(false)
      setStartTime(Date.now())
    } catch {
      message.error('加载复习任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const submit = async (quality: number) => {
    if (!current) return
    try {
      await reviewApi.submitReview(current.id, quality)
      setFlipped(false)
      if (index + 1 >= cards.length) {
        const elapsed = Math.round((Date.now() - startTime) / 1000)
        const minutes = Math.floor(elapsed / 60)
        const seconds = elapsed % 60
        message.success(`今日复习完成！用时 ${minutes > 0 ? `${minutes}分` : ''}${seconds}秒`)
        await fetchData()
      } else {
        setIndex(index + 1)
      }
    } catch {
      message.error('提交评分失败')
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="!mb-1">间隔复习</Title>
          <Text type="secondary">翻卡片后按真实记忆程度评分</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500">今日待复习</div>
          <div className="text-3xl font-semibold">{stats?.due_today ?? 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500">全部卡片</div>
          <div className="text-3xl font-semibold">{stats?.total_cards ?? 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-500">已掌握知识点</div>
          <div className="text-3xl font-semibold">{stats?.mastered_count ?? 0}</div>
        </div>
      </div>

      {cards.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-10">
          <Empty description="今天没有待复习卡片" />
        </div>
      ) : (
        <>
          <div className="mb-4">
            <Progress percent={Math.round((completed / cards.length) * 100)} />
            <Text type="secondary">第 {index + 1} / {cards.length} 张</Text>
          </div>

          <button
            type="button"
            onClick={() => setFlipped(!flipped)}
            className="w-full min-h-[280px] bg-white border border-gray-200 rounded-lg p-8 text-left shadow-sm hover:border-indigo-300 transition"
          >
            <Space className="mb-4">
              <Tag color="blue">{cardTypeLabel[current.card_type]}</Tag>
              <Text type="secondary">{flipped ? '答案' : '问题'}</Text>
            </Space>
            <div className="text-2xl font-semibold leading-relaxed whitespace-pre-wrap">
              {flipped ? current.answer : current.question}
            </div>
            <div className="mt-6 text-gray-400 flex items-center gap-2">
              <EyeOutlined /> 点击卡片翻面
            </div>
          </button>

          <div className="mt-6 grid grid-cols-3 gap-4">
            <button
              type="button"
              disabled={!flipped}
              onClick={() => submit(0)}
              className="p-4 rounded-lg border-2 border-red-300 bg-red-50 hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed transition text-center"
            >
              <div className="text-lg font-semibold text-red-600">忘了</div>
              <div className="text-xs text-red-400 mt-1">很快再看</div>
            </button>
            <button
              type="button"
              disabled={!flipped}
              onClick={() => submit(3)}
              className="p-4 rounded-lg border-2 border-orange-300 bg-orange-50 hover:bg-orange-100 disabled:opacity-40 disabled:cursor-not-allowed transition text-center"
            >
              <div className="text-lg font-semibold text-orange-600">模糊</div>
              <div className="text-xs text-orange-400 mt-1">明天再看</div>
            </button>
            <button
              type="button"
              disabled={!flipped}
              onClick={() => submit(5)}
              className="p-4 rounded-lg border-2 border-green-300 bg-green-50 hover:bg-green-100 disabled:opacity-40 disabled:cursor-not-allowed transition text-center"
            >
              <div className="text-lg font-semibold text-green-600">记住</div>
              <div className="text-xs text-green-400 mt-1">等更久再看</div>
            </button>
          </div>
        </>
      )}
    </div>
  )
}

