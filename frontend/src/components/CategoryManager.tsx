import { useState, useEffect, useCallback } from 'react'
import { Modal, List, Button, Input, Space, Popconfirm, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { categoryApi, type Category } from '../api/categories'

interface CategoryManagerProps {
  open: boolean
  onClose: () => void
  onUpdated: () => void
}

export default function CategoryManager({ open, onClose, onUpdated }: CategoryManagerProps) {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')

  const fetchCategories = useCallback(async () => {
    setLoading(true)
    try {
      const res = await categoryApi.list()
      setCategories(res.data)
    } catch {
      message.error('加载分类失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) fetchCategories()
  }, [open, fetchCategories])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      await categoryApi.create({ name: newName.trim(), description: newDesc.trim() || undefined })
      message.success('分类已创建')
      setNewName('')
      setNewDesc('')
      setAdding(false)
      fetchCategories()
      onUpdated()
    } catch {
      message.error('创建失败')
    }
  }

  const handleUpdate = async (id: string) => {
    if (!editName.trim()) return
    try {
      await categoryApi.update(id, { name: editName.trim(), description: editDesc.trim() || undefined })
      message.success('分类已更新')
      setEditingId(null)
      fetchCategories()
      onUpdated()
    } catch {
      message.error('更新失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await categoryApi.delete(id)
      message.success('分类已删除')
      fetchCategories()
      onUpdated()
    } catch {
      message.error('删除失败')
    }
  }

  const startEdit = (cat: Category) => {
    setEditingId(cat.id)
    setEditName(cat.name)
    setEditDesc(cat.description || '')
  }

  return (
    <Modal
      title="分类管理"
      open={open}
      onCancel={onClose}
      footer={null}
      width={520}
    >
      <List
        loading={loading}
        dataSource={categories}
        locale={{ emptyText: '暂无分类，点击下方按钮创建' }}
        renderItem={(cat) => (
          <List.Item
            actions={
              editingId === cat.id
                ? [
                    <Button type="link" size="small" onClick={() => handleUpdate(cat.id)}>保存</Button>,
                    <Button type="link" size="small" onClick={() => setEditingId(null)}>取消</Button>,
                  ]
                : [
                    <Button type="link" size="small" icon={<EditOutlined />} onClick={() => startEdit(cat)}>编辑</Button>,
                    <Popconfirm title="删除分类后，关联知识点的分类将被清空" onConfirm={() => handleDelete(cat.id)}>
                      <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
                    </Popconfirm>,
                  ]
            }
          >
            {editingId === cat.id ? (
              <Space direction="vertical" className="w-full">
                <Input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="分类名称"
                  maxLength={100}
                />
                <Input
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  placeholder="描述（可选）"
                />
              </Space>
            ) : (
              <List.Item.Meta
                title={cat.name}
                description={cat.description || undefined}
              />
            )}
          </List.Item>
        )}
      />

      {adding ? (
        <div className="mt-3 space-y-2">
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="分类名称"
            maxLength={100}
            onPressEnter={handleCreate}
          />
          <Input
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="描述（可选）"
          />
          <Space>
            <Button type="primary" size="small" onClick={handleCreate}>创建</Button>
            <Button size="small" onClick={() => { setAdding(false); setNewName(''); setNewDesc('') }}>取消</Button>
          </Space>
        </div>
      ) : (
        <Button
          type="dashed"
          block
          icon={<PlusOutlined />}
          className="mt-3"
          onClick={() => setAdding(true)}
        >
          新建分类
        </Button>
      )}
    </Modal>
  )
}
