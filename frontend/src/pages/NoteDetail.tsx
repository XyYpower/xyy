import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Input, Select, Tooltip, Spin, message } from 'antd'
import { ArrowLeftOutlined, SaveOutlined, StarOutlined, StarFilled, ThunderboltOutlined } from '@ant-design/icons'
import { noteApi, type Note } from '../api/notes'
import { reviewApi } from '../api/review'
import { categoryApi, type Category } from '../api/categories'
import { tagApi, type Tag as TagType } from '../api/tags'
import MarkdownEditor from '../components/MarkdownEditor'

const masteryOptions = [
  { label: '未学', value: 0 },
  { label: '学习中', value: 1 },
  { label: '已掌握', value: 2 },
]

export default function NoteDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [note, setNote] = useState<Note | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [masteryLevel, setMasteryLevel] = useState(0)
  const [isFavorite, setIsFavorite] = useState(false)
  const [tagNames, setTagNames] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)

  const [categories, setCategories] = useState<Category[]>([])
  const [allTags, setAllTags] = useState<TagType[]>([])

  // 追踪初始值用于判断是否有未保存更改
  const initialValues = useRef<string>('')
  const handleSaveRef = useRef<() => Promise<void>>(() => Promise.resolve())

  const markDirty = useCallback(() => {
    if (!dirty) setDirty(true)
  }, [dirty])

  useEffect(() => {
    if (id) fetchNote()
    fetchDropdownData()
  }, [id])

  // Ctrl+S 快捷键保存
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSaveRef.current()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // 离开页面前提醒
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])

  const fetchNote = async () => {
    setLoading(true)
    try {
      const res = await noteApi.get(id!)
      const n = res.data
      setNote(n)
      setTitle(n.title)
      setContent(n.content)
      setCategoryId(n.category?.id || null)
      setMasteryLevel(n.mastery_level)
      setIsFavorite(n.is_favorite)
      setTagNames(n.tags.map(t => t.name))
      // 记录初始值
      initialValues.current = JSON.stringify({
        title: n.title, content: n.content, category: n.category?.id,
        mastery: n.mastery_level, fav: n.is_favorite, tags: n.tags.map(t => t.name).sort(),
      })
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchDropdownData = async () => {
    try {
      const [catRes, tagRes] = await Promise.all([categoryApi.list(), tagApi.list()])
      setCategories(catRes.data)
      setAllTags(tagRes.data)
    } catch {
      // 静默失败
    }
  }

  const handleSave = async () => {
    if (!id || saving) return
    setSaving(true)
    try {
      const res = await noteApi.update(id, {
        title,
        content,
        category_id: categoryId,
        mastery_level: masteryLevel,
        is_favorite: isFavorite,
        tag_names: tagNames,
      })
      setNote(res.data)
      setDirty(false)
      // 更新初始值
      initialValues.current = JSON.stringify({
        title, content, category: categoryId,
        mastery: masteryLevel, fav: isFavorite, tags: [...tagNames].sort(),
      })
      fetchDropdownData()
      message.success('已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }
  handleSaveRef.current = handleSave

  const handleGenerateCards = async () => {
    if (!id) return
    setGenerating(true)
    try {
      const res = await reviewApi.generateCards(id)
      message.success(`已生成 ${res.data.length} 张复习卡片`)
    } catch {
      message.error('生成卡片失败')
    } finally {
      setGenerating(false)
    }
  }

  // 监听内容变化标记 dirty
  useEffect(() => {
    if (!loading && initialValues.current) {
      const current = JSON.stringify({
        title, content, category: categoryId,
        mastery: masteryLevel, fav: isFavorite, tags: [...tagNames].sort(),
      })
      setDirty(current !== initialValues.current)
    }
  }, [title, content, categoryId, masteryLevel, isFavorite, tagNames, loading])

  if (loading) {
    return (
      <div className="flex justify-center items-center p-16">
        <Spin size="large" />
      </div>
    )
  }

  if (!note) return <div className="p-8 text-center text-gray-400">知识点不存在</div>

  return (
    <div className="max-w-5xl mx-auto">
      {/* 顶部操作栏 */}
      <div className="flex items-center gap-3 mb-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/notes')}>
          返回
        </Button>
        <Input
          value={title}
          onChange={(e) => { setTitle(e.target.value); markDirty() }}
          className="text-xl font-bold flex-1"
          variant="borderless"
          placeholder="知识点标题"
        />
        {dirty && <span className="text-xs text-orange-500">未保存</span>}
        <Tooltip title={isFavorite ? '取消收藏' : '收藏'}>
          <Button
            type="text"
            icon={isFavorite ? <StarFilled className="text-yellow-500 text-lg" /> : <StarOutlined className="text-lg" />}
            onClick={() => { setIsFavorite(!isFavorite); markDirty() }}
          />
        </Tooltip>
        <Tooltip title="Ctrl+S">
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存
          </Button>
        </Tooltip>
        <Tooltip title="为这个知识点生成复习卡片">
          <Button icon={<ThunderboltOutlined />} loading={generating} onClick={handleGenerateCards}>
            生成卡片
          </Button>
        </Tooltip>
      </div>

      {/* 元信息区 */}
      <div className="flex flex-wrap items-center gap-4 mb-4 px-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">分类：</span>
          <Select
            value={categoryId}
            onChange={(v) => { setCategoryId(v); markDirty() }}
            placeholder="选择分类"
            allowClear
            className="min-w-[140px]"
            size="small"
            options={categories.map(c => ({ label: c.name, value: c.id }))}
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">掌握度：</span>
          <Select
            value={masteryLevel}
            onChange={(v) => { setMasteryLevel(v); markDirty() }}
            className="min-w-[100px]"
            size="small"
            options={masteryOptions}
          />
        </div>
      </div>

      {/* 标签区 */}
      <div className="mb-4 px-1">
        <Select
          mode="tags"
          value={tagNames}
          onChange={(v) => { setTagNames(v); markDirty() }}
          placeholder="添加标签..."
          className="w-full"
          size="small"
          tokenSeparators={[',']}
          options={allTags.map(t => ({ label: t.name, value: t.name }))}
        />
      </div>

      {/* Markdown 编辑器 */}
      <MarkdownEditor
        value={content}
        onChange={(v) => { setContent(v); markDirty() }}
        placeholder="开始写知识点内容... (支持 Markdown)"
      />

      {/* 底部信息 */}
      <div className="mt-3 px-1 text-xs text-gray-400 flex gap-4">
        <span>来源：{note.source_type === 'manual' ? '手动创建' : note.source_type === 'imported' ? '导入' : 'AI 生成'}</span>
        <span>创建于 {new Date(note.created_at).toLocaleString()}</span>
        <span>更新于 {new Date(note.updated_at).toLocaleString()}</span>
      </div>
    </div>
  )
}
