import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Empty,
  Input,
  List,
  Modal,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  CheckCircleOutlined,
  CodeOutlined,
  EditOutlined,
  FileTextOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import { importApi, type ExtractionDraft, type ImportSourceType } from '../api/import'

const { Text, Title } = Typography
const { TextArea } = Input

const tabItems = [
  { key: 'text', label: '粘贴文本', icon: <FileTextOutlined /> },
  { key: 'url', label: '粘贴 URL', icon: <LinkOutlined /> },
  { key: 'code', label: '粘贴代码', icon: <CodeOutlined /> },
]

const sourceLabels: Record<ImportSourceType, string> = {
  text: '文本',
  url: 'URL',
  code: '代码',
}

export default function Import() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ImportSourceType>('text')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState<string | undefined>('java')
  const [jobStatus, setJobStatus] = useState<string | null>(null)
  const [jobError, setJobError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<ExtractionDraft[]>([])
  const [extracting, setExtracting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set())
  const [editingDraft, setEditingDraft] = useState<ExtractionDraft | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')
  const [savingEdit, setSavingEdit] = useState(false)

  const selectedCount = useMemo(() => drafts.filter((draft) => draft.is_selected).length, [drafts])

  const setDraft = (updated: ExtractionDraft) => {
    setDrafts((current) => current.map((draft) => (draft.id === updated.id ? updated : draft)))
  }

  const getCurrentPayload = () => {
    if (activeTab === 'text') return text.trim()
    if (activeTab === 'url') return url.trim()
    return code.trim()
  }

  const extract = async () => {
    const payload = getCurrentPayload()
    if (!payload) {
      message.warning(`请先填写${sourceLabels[activeTab]}内容`)
      return
    }
    if (activeTab === 'text' && payload.length < 10) {
      message.warning('文本至少 10 个字符')
      return
    }
    if (activeTab === 'code' && payload.length < 5) {
      message.warning('代码至少 5 个字符')
      return
    }

    setExtracting(true)
    setJobError(null)
    try {
      const response =
        activeTab === 'text'
          ? await importApi.importText(payload)
          : activeTab === 'url'
            ? await importApi.importUrl(payload)
            : await importApi.importCode(payload, language)

      setJobId(response.data.job.id)
      setJobStatus(response.data.job.status)
      setJobError(response.data.job.error_message)
      setDrafts(response.data.drafts)
      if (response.data.job.status === 'failed') {
        message.error(response.data.job.error_message || '提取失败')
      } else {
        message.success(`已提取 ${response.data.drafts.length} 个候选知识点`)
      }
    } catch {
      message.error('提取失败')
    } finally {
      setExtracting(false)
    }
  }

  const toggleDraft = async (draft: ExtractionDraft, checked: boolean) => {
    setUpdatingIds((current) => new Set(current).add(draft.id))
    try {
      const response = await importApi.updateDraft(draft.id, { is_selected: checked })
      setDraft(response.data)
    } catch {
      message.error('更新草稿失败')
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current)
        next.delete(draft.id)
        return next
      })
    }
  }

  const setAllSelected = async (checked: boolean) => {
    const targets = drafts.filter((draft) => draft.is_selected !== checked)
    if (targets.length === 0) return
    setUpdatingIds((current) => {
      const next = new Set(current)
      targets.forEach((draft) => next.add(draft.id))
      return next
    })
    try {
      const results = await Promise.allSettled(
        targets.map((draft) => importApi.updateDraft(draft.id, { is_selected: checked }))
      )
      const successfulDrafts = results
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value.data)
      const failedCount = results.length - successfulDrafts.length

      setDrafts((current) =>
        current.map((draft) => successfulDrafts.find((updated) => updated.id === draft.id) ?? draft)
      )
      if (failedCount > 0) {
        message.error(`${failedCount} 个草稿更新失败`)
      }
    } finally {
      setUpdatingIds(new Set())
    }
  }

  const openEdit = (draft: ExtractionDraft) => {
    setEditingDraft(draft)
    setEditTitle(draft.title)
    setEditContent(draft.content)
  }

  const saveEdit = async () => {
    if (!editingDraft) return
    if (!editTitle.trim()) {
      message.warning('标题不能为空')
      return
    }
    setSavingEdit(true)
    try {
      const response = await importApi.updateDraft(editingDraft.id, {
        title: editTitle.trim(),
        content: editContent.trim(),
      })
      setDraft(response.data)
      setEditingDraft(null)
      message.success('草稿已更新')
    } catch {
      message.error('保存失败')
    } finally {
      setSavingEdit(false)
    }
  }

  const confirmImport = async () => {
    if (!jobId || selectedCount === 0) return
    setConfirming(true)
    try {
      await importApi.confirmImport(jobId)
      message.success(`已导入 ${selectedCount} 个知识点`)
      navigate('/notes')
    } catch {
      message.error('确认导入失败')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3 mb-6">
        <div>
          <Title level={2} className="!mb-1">导入知识</Title>
          <Text type="secondary">从文章、面经或代码中提取可复习的知识点</Text>
        </div>
        {drafts.length > 0 && (
          <Space wrap>
            <Button onClick={() => setAllSelected(true)} disabled={selectedCount === drafts.length}>
              全选
            </Button>
            <Button onClick={() => setAllSelected(false)} disabled={selectedCount === 0}>
              全不选
            </Button>
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              disabled={!jobId || selectedCount === 0 || jobStatus !== 'draft'}
              loading={confirming}
              onClick={confirmImport}
            >
              确认导入 {selectedCount} 个
            </Button>
          </Space>
        )}
      </div>

      <Card className="mb-5">
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as ImportSourceType)}
          items={tabItems.map((item) => ({
            key: item.key,
            label: (
              <Space>
                {item.icon}
                {item.label}
              </Space>
            ),
          }))}
        />

        {activeTab === 'text' && (
          <TextArea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={10}
            placeholder="粘贴技术文章、面经、学习笔记..."
          />
        )}
        {activeTab === 'url' && (
          <Input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com/article"
            prefix={<LinkOutlined />}
          />
        )}
        {activeTab === 'code' && (
          <Space direction="vertical" className="w-full" size="middle">
            <Select
              value={language}
              onChange={setLanguage}
              className="w-48"
              options={[
                { value: 'java', label: 'Java' },
                { value: 'python', label: 'Python' },
                { value: 'javascript', label: 'JavaScript' },
                { value: 'typescript', label: 'TypeScript' },
                { value: 'sql', label: 'SQL' },
                { value: 'other', label: '其他' },
              ]}
            />
            <TextArea
              value={code}
              onChange={(event) => setCode(event.target.value)}
              rows={12}
              placeholder="粘贴代码片段..."
              className="font-mono"
            />
          </Space>
        )}

        <div className="mt-4 flex justify-end">
          <Button type="primary" loading={extracting} onClick={extract}>
            开始提取
          </Button>
        </div>
      </Card>

      {jobError && (
        <Alert
          className="mb-5"
          type="error"
          showIcon
          message="提取失败"
          description={jobError}
        />
      )}

      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <Title level={4} className="!mb-1">AI 提取结果</Title>
            <Text type="secondary">{drafts.length > 0 ? `当前任务状态：${jobStatus}` : '暂无草稿'}</Text>
          </div>
          {drafts.length > 0 && <Tag color="blue">{selectedCount} / {drafts.length} 已选择</Tag>}
        </div>

        {drafts.length === 0 ? (
          <Empty description="提取后会在这里显示候选知识点" />
        ) : (
          <List
            itemLayout="vertical"
            dataSource={drafts}
            renderItem={(draft) => (
              <List.Item
                key={draft.id}
                className="!px-0"
                actions={[
                  <Button
                    key="edit"
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => openEdit(draft)}
                  >
                    编辑
                  </Button>,
                ]}
              >
                <div className="flex gap-3">
                  <Checkbox
                    className="mt-1"
                    checked={draft.is_selected}
                    disabled={updatingIds.has(draft.id)}
                    onChange={(event) => toggleDraft(draft, event.target.checked)}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-base font-semibold text-gray-900 break-words">{draft.title}</div>
                    <div className="text-gray-500 mt-2 whitespace-pre-wrap line-clamp-3">{draft.content}</div>
                  </div>
                </div>
              </List.Item>
            )}
          />
        )}
      </Card>

      <Modal
        title="编辑草稿"
        open={!!editingDraft}
        confirmLoading={savingEdit}
        onOk={saveEdit}
        onCancel={() => setEditingDraft(null)}
        okText="保存"
        cancelText="取消"
        width={720}
      >
        <Space direction="vertical" className="w-full" size="middle">
          <Input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} placeholder="标题" />
          <TextArea
            value={editContent}
            onChange={(event) => setEditContent(event.target.value)}
            rows={10}
            placeholder="内容"
          />
        </Space>
      </Modal>
    </div>
  )
}
