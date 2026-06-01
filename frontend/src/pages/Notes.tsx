import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Card, Tag, Empty, Space, Modal, message } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons'
import { noteApi, type Note } from '../api/notes'

export default function Notes() {
  const navigate = useNavigate()
  const [notes, setNotes] = useState<Note[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchNotes()
  }, [page])

  const fetchNotes = async () => {
    setLoading(true)
    try {
      const res = await noteApi.list({ page, page_size: 20, keyword: keyword || undefined })
      setNotes(res.data.items)
      setTotal(res.data.total)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      const res = await noteApi.create({ title: '无标题笔记', content: '' })
      navigate(`/notes/${res.data.id}`)
    } catch {
      message.error('创建失败')
    }
  }

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除？',
      content: '删除后不可恢复',
      onOk: async () => {
        await noteApi.delete(id)
        message.success('已删除')
        fetchNotes()
      },
    })
  }

  const handleSearch = () => {
    setPage(1)
    fetchNotes()
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold m-0">知识点</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建知识点
        </Button>
      </div>

      <div className="mb-4 flex gap-2">
        <Input
          placeholder="搜索知识点..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={handleSearch}
          prefix={<SearchOutlined />}
          className="max-w-sm"
        />
        <Button onClick={handleSearch}>搜索</Button>
      </div>

      {notes.length === 0 && !loading ? (
        <Empty description="还没有知识点，点击上方按钮创建" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {notes.map((note) => (
            <Card
              key={note.id}
              hoverable
              onClick={() => navigate(`/notes/${note.id}`)}
              className="cursor-pointer"
            >
              <div className="flex justify-between items-start">
                <h3 className="text-lg font-semibold m-0 line-clamp-1">{note.title}</h3>
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(note.id)
                  }}
                />
              </div>
              {note.summary && (
                <p className="text-gray-500 mt-2 mb-0 line-clamp-2">{note.summary}</p>
              )}
              <div className="mt-3 flex gap-1 flex-wrap">
                {note.tags.map((tag) => (
                  <Tag key={tag.id} color="blue">{tag.name}</Tag>
                ))}
              </div>
              <div className="mt-2 text-xs text-gray-400">
                {new Date(note.updated_at).toLocaleDateString()}
                <span className="ml-2">
                  {note.mastery_level === 2 ? '已掌握' : note.mastery_level === 1 ? '学习中' : '未学'}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {total > 20 && (
        <div className="mt-4 text-center">
          <Space>
            <Button disabled={page === 1} onClick={() => setPage(page - 1)}>上一页</Button>
            <span>{page} / {Math.ceil(total / 20)}</span>
            <Button disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>下一页</Button>
          </Space>
        </div>
      )}
    </div>
  )
}
