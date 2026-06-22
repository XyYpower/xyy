import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Input, Card, Tag, Empty, Space, Modal, Switch, message } from 'antd'
import { PlusOutlined, SearchOutlined, DeleteOutlined, StarOutlined, StarFilled, SettingOutlined } from '@ant-design/icons'
import { noteApi, type Note } from '../api/notes'
import { categoryApi, type Category } from '../api/categories'
import CategoryManager from '../components/CategoryManager'

export default function Notes() {
  const navigate = useNavigate()
  const [notes, setNotes] = useState<Note[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')
  const [categoryId, setCategoryId] = useState<string | undefined>()
  const [onlyFavorites, setOnlyFavorites] = useState(false)
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryManagerOpen, setCategoryManagerOpen] = useState(false)
  const [presetLoading, setPresetLoading] = useState(false)

  // Quick add state
  const [quickTitle, setQuickTitle] = useState('')
  const [quickContent, setQuickContent] = useState('')
  const [quickAdding, setQuickAdding] = useState(false)

  const fetchCategories = async () => {
    try {
      const res = await categoryApi.list()
      setCategories(res.data)
    } catch {
      // silent
    }
  }

  useEffect(() => {
    fetchCategories()
  }, [])

  useEffect(() => {
    fetchNotes()
  }, [page, categoryId, onlyFavorites])

  const fetchNotes = async () => {
    setLoading(true)
    try {
      const res = await noteApi.list({
        page,
        page_size: 20,
        keyword: keyword || undefined,
        category_id: categoryId,
        is_favorite: onlyFavorites ? true : undefined,
      })
      setNotes(res.data.items)
      setTotal(res.data.total)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleQuickAdd = async () => {
    const title = quickTitle.trim()
    if (!title) {
      message.warning('请输入标题')
      return
    }
    setQuickAdding(true)
    try {
      const res = await noteApi.create({ title, content: quickContent.trim() })
      message.success('已创建')
      setQuickTitle('')
      setQuickContent('')
      navigate(`/notes/${res.data.id}`)
    } catch {
      message.error('创建失败')
    } finally {
      setQuickAdding(false)
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

  const handleToggleFavorite = async (note: Note) => {
    try {
      await noteApi.update(note.id, { is_favorite: !note.is_favorite })
      setNotes(notes.map(n => n.id === note.id ? { ...n, is_favorite: !n.is_favorite } : n))
    } catch {
      message.error('操作失败')
    }
  }

  const handleSearch = () => {
    setPage(1)
    fetchNotes()
  }

  const handleCategoryFilter = (id: string | undefined) => {
    setCategoryId(id)
    setPage(1)
  }

  const handleSetupPresets = async () => {
    setPresetLoading(true)
    try {
      const res = await categoryApi.createPresets()
      setCategories(res.data)
      message.success(`已创建 ${res.data.length} 个八股分类`)
    } catch {
      message.error('创建分类失败')
    } finally {
      setPresetLoading(false)
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold m-0">知识点</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建知识点
        </Button>
      </div>

      {/* Quick add bar */}
      <Card size="small" className="mb-4">
        <div className="flex gap-2">
          <Input
            placeholder="快速添加：输入标题..."
            value={quickTitle}
            onChange={(e) => setQuickTitle(e.target.value)}
            onPressEnter={handleQuickAdd}
            className="flex-1"
          />
          <Input
            placeholder="内容（可选，支持 Markdown）"
            value={quickContent}
            onChange={(e) => setQuickContent(e.target.value)}
            onPressEnter={handleQuickAdd}
            className="flex-1"
          />
          <Button type="primary" icon={<PlusOutlined />} loading={quickAdding} onClick={handleQuickAdd}>
            添加
          </Button>
        </div>
      </Card>

      {/* Category chips + search */}
      <div className="mb-4 space-y-3">
        <div className="flex flex-wrap gap-2 items-center">
          <Input
            placeholder="搜索知识点..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            prefix={<SearchOutlined />}
            className="max-w-sm"
          />
          <Button onClick={handleSearch}>搜索</Button>
          <div className="flex items-center gap-1 ml-2">
            <Switch
              size="small"
              checked={onlyFavorites}
              onChange={(v) => { setOnlyFavorites(v); setPage(1) }}
            />
            <span className="text-sm text-gray-500">只看收藏</span>
          </div>
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => setCategoryManagerOpen(true)}
            className="ml-auto"
          >
            分类管理
          </Button>
        </div>

        {/* Category filter chips */}
        <div className="flex flex-wrap gap-2 items-center">
          <Tag
            className={`cursor-pointer px-3 py-1 ${!categoryId ? 'border-indigo-500 text-indigo-600' : ''}`}
            onClick={() => handleCategoryFilter(undefined)}
          >
            全部
          </Tag>
          {categories.map((cat) => (
            <Tag
              key={cat.id}
              className={`cursor-pointer px-3 py-1 ${categoryId === cat.id ? 'border-indigo-500 text-indigo-600' : ''}`}
              onClick={() => handleCategoryFilter(cat.id)}
            >
              {cat.name}
            </Tag>
          ))}
          {categories.length === 0 && (
            <Button size="small" type="dashed" loading={presetLoading} onClick={handleSetupPresets}>
              初始化八股分类
            </Button>
          )}
        </div>
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
                <h3 className="text-lg font-semibold m-0 line-clamp-1 flex-1">{note.title}</h3>
                <div className="flex items-center gap-1">
                  <Button
                    type="text"
                    size="small"
                    icon={note.is_favorite ? <StarFilled className="text-yellow-500" /> : <StarOutlined />}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleToggleFavorite(note)
                    }}
                  />
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
              </div>
              {note.category && (
                <Tag color="purple" className="mt-1">{note.category.name}</Tag>
              )}
              {/* Content preview */}
              {note.content && (
                <p className="text-gray-500 mt-2 mb-0 text-sm line-clamp-3 font-mono">
                  {note.content.slice(0, 120)}
                </p>
              )}
              {!note.content && note.summary && (
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
                  {note.mastery_level === 2 ? '✅ 已掌握' : note.mastery_level === 1 ? '📖 学习中' : '📝 未学'}
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

      <CategoryManager
        open={categoryManagerOpen}
        onClose={() => setCategoryManagerOpen(false)}
        onUpdated={fetchCategories}
      />
    </div>
  )
}
