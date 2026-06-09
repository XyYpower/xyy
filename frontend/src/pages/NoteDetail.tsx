import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Input, Select, Tooltip, message } from 'antd'
import { ArrowLeftOutlined, SaveOutlined, StarOutlined, StarFilled } from '@ant-design/icons'
import { noteApi, type Note } from '../api/notes'
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

  // 下拉数据
  const [categories, setCategories] = useState<Category[]>([])
  const [allTags, setAllTags] = useState<TagType[]>([])

  useEffect(() => {
    if (id) fetchNote()
    fetchDropdownData()
  }, [id])

  const fetchNote = async () => {
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
    } catch {
      message.error('加载失败')
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
    if (!id) return
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
      // 保存后刷新标签列表（可能有新标签被创建）
      fetchDropdownData()
      message.success('已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!note) return <div className="p-8 text-center text-gray-400">加载中...</div>

  return (
    <div className="max-w-5xl mx-auto">
      {/* 顶部操作栏 */}
      <div className="flex items-center gap-3 mb-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/notes')}>
          返回
        </Button>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="text-xl font-bold flex-1"
          variant="borderless"
          placeholder="知识点标题"
        />
        <Tooltip title={isFavorite ? '取消收藏' : '收藏'}>
          <Button
            type="text"
            icon={isFavorite ? <StarFilled className="text-yellow-500 text-lg" /> : <StarOutlined className="text-lg" />}
            onClick={() => setIsFavorite(!isFavorite)}
          />
        </Tooltip>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存
        </Button>
      </div>

      {/* 元信息区 */}
      <div className="flex flex-wrap items-center gap-4 mb-4 px-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">分类：</span>
          <Select
            value={categoryId}
            onChange={setCategoryId}
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
            onChange={setMasteryLevel}
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
          onChange={setTagNames}
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
        onChange={setContent}
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
