import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Input, Tag, message } from 'antd'
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons'
import { noteApi, type Note } from '../api/notes'

export default function NoteDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [note, setNote] = useState<Note | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (id) fetchNote()
  }, [id])

  const fetchNote = async () => {
    try {
      const res = await noteApi.get(id!)
      setNote(res.data)
      setTitle(res.data.title)
      setContent(res.data.content)
    } catch {
      message.error('加载失败')
    }
  }

  const handleSave = async () => {
    if (!id) return
    setSaving(true)
    try {
      await noteApi.update(id, { title, content })
      message.success('已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!note) return <div>加载中...</div>

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/notes')}>
          返回
        </Button>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="text-xl font-bold flex-1"
          variant="borderless"
          placeholder="笔记标题"
        />
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存
        </Button>
      </div>

      <div className="mb-3 flex gap-1">
        {note.tags.map((tag) => (
          <Tag key={tag.id} color="blue">{tag.name}</Tag>
        ))}
      </div>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="w-full min-h-[60vh] p-4 rounded-lg border border-gray-200 bg-white resize-y font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
        placeholder="开始写笔记... (支持 Markdown)"
      />
    </div>
  )
}
