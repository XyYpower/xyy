import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Input, Select, Tabs, Typography, message } from 'antd'
import { ThunderboltOutlined, FileTextOutlined, LinkOutlined, CodeOutlined } from '@ant-design/icons'
import { importApi, type ImportResult } from '../api/import'
import { categoryApi, type Category } from '../api/categories'

const { Title, Text } = Typography
const { TextArea } = Input

const EXAMPLE_CONTENT = `## 进程和线程的区别

进程是操作系统分配资源的基本单位，线程是 CPU 调度的基本单位。
一个进程可以包含多个线程，线程共享进程的内存空间。
进程之间相互隔离，通信需要 IPC（管道、消息队列、共享内存等）。
创建/销毁进程的开销比线程大，线程切换比进程切换快。

## TCP 三次握手

1. 客户端发送 SYN（seq=x），进入 SYN_SENT 状态
2. 服务端收到后回复 SYN+ACK（seq=y, ack=x+1），进入 SYN_RCVD 状态
3. 客户端发送 ACK（ack=y+1），双方进入 ESTABLISHED 状态

为什么是三次？防止历史重复连接的初始化，两次握手无法确认客户端的接收能力。

## HashMap 底层原理

JDK 8 中 HashMap 采用 数组 + 链表 + 红黑树 结构。
- 默认初始容量 16，负载因子 0.75
- put 流程：计算 hash → 定位桶 → 空则直接放 → 非空则链表/红黑树插入
- 链表长度 >= 8 且数组长度 >= 64 时，链表转红黑树
- 红黑树节点 <= 6 时退化为链表
- 扩容：容量翻倍，重新 hash 分布

## volatile 关键字

volatile 保证可见性和禁止指令重排序，但不保证原子性。
- 可见性：修改后立即刷新到主内存，其他线程读取时从主内存获取
- 禁止重排序：通过内存屏障（Memory Barrier）实现
- 典型场景：DCL 单例模式中防止指令重排

## Redis 持久化方式

RDB（快照）：定时将内存数据dump到磁盘，恢复快但可能丢数据。
AOF（追加日志）：记录每条写命令，数据安全但文件大、恢复慢。
Redis 4.0+ 支持混合持久化：RDB 做全量 + AOF 做增量。
`

export default function Import() {
  const navigate = useNavigate()
  const [quickMarkdown, setQuickMarkdown] = useState('')
  const [categoryId, setCategoryId] = useState<string | undefined>()
  const [categories, setCategories] = useState<Category[]>([])
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<{ count: number } | null>(null)

  // 传统导入
  const [legacyText, setLegacyText] = useState('')
  const [legacyUrl, setLegacyUrl] = useState('')
  const [legacyCode, setLegacyCode] = useState('')
  const [legacyLanguage, setLegacyLanguage] = useState('')
  const [legacyResult, setLegacyResult] = useState<ImportResult | null>(null)
  const [legacyLoading, setLegacyLoading] = useState(false)

  useEffect(() => {
    categoryApi.list().then(res => setCategories(res.data)).catch(() => {})
  }, [])

  const handleQuickImport = async () => {
    const md = quickMarkdown.trim()
    if (!md) {
      message.warning('请粘贴 Markdown 内容')
      return
    }
    setImporting(true)
    setResult(null)
    try {
      const res = await importApi.quickImport(md, categoryId)
      setResult({ count: res.data.count })
      message.success(`成功导入 ${res.data.count} 个知识点，复习卡片正在后台生成`)
    } catch {
      message.error('导入失败')
    } finally {
      setImporting(false)
    }
  }

  const handleLoadExample = () => {
    setQuickMarkdown(EXAMPLE_CONTENT)
    message.info('已加载示例内容，可以直接导入或修改后再导入')
  }

  // 传统文本导入
  const handleLegacyText = async () => {
    if (!legacyText.trim()) return
    setLegacyLoading(true)
    try {
      const res = await importApi.importText(legacyText)
      setLegacyResult(res.data)
    } catch {
      message.error('导入失败')
    } finally {
      setLegacyLoading(false)
    }
  }

  const handleLegacyUrl = async () => {
    if (!legacyUrl.trim()) return
    setLegacyLoading(true)
    try {
      const res = await importApi.importUrl(legacyUrl)
      setLegacyResult(res.data)
    } catch {
      message.error('URL 抓取失败')
    } finally {
      setLegacyLoading(false)
    }
  }

  const handleLegacyCode = async () => {
    if (!legacyCode.trim()) return
    setLegacyLoading(true)
    try {
      const res = await importApi.importCode(legacyCode, legacyLanguage)
      setLegacyResult(res.data)
    } catch {
      message.error('导入失败')
    } finally {
      setLegacyLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'quick',
      label: <span><ThunderboltOutlined /> 快速导入</span>,
      children: (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <Text strong>格式说明：</Text>
            <ul className="text-sm text-gray-600 mt-2 mb-0 space-y-1">
              <li>每个知识点用 <code>## 标题</code> 分隔</li>
              <li>标题下面写内容，支持 Markdown 格式和代码块</li>
              <li>一键导入，自动创建知识点并生成复习卡片</li>
            </ul>
          </div>

          <div className="flex gap-2">
            <Select
              placeholder="选择分类（可选）"
              value={categoryId}
              onChange={setCategoryId}
              allowClear
              className="w-48"
              options={categories.map(c => ({ label: c.name, value: c.id }))}
            />
            <Button onClick={handleLoadExample}>加载示例内容</Button>
          </div>

          <TextArea
            value={quickMarkdown}
            onChange={(e) => setQuickMarkdown(e.target.value)}
            placeholder={`在此粘贴 Markdown 内容，格式如下：\n\n## 知识点标题 1\n内容...\n\n## 知识点标题 2\n内容...`}
            rows={16}
            className="font-mono text-sm"
          />

          <div className="flex items-center gap-4">
            <Button
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              loading={importing}
              onClick={handleQuickImport}
            >
              快速导入
            </Button>
            {result && (
              <Text type="success">
                已导入 {result.count} 个知识点
                <Button type="link" onClick={() => navigate('/notes')}>查看知识点 →</Button>
                <Button type="link" onClick={() => navigate('/review')}>去复习 →</Button>
              </Text>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'text',
      label: <span><FileTextOutlined /> 文本导入</span>,
      children: (
        <div className="space-y-4">
          <Text type="secondary">粘贴文本，AI 会自动提取知识点（需配置 API Key）</Text>
          <TextArea
            value={legacyText}
            onChange={(e) => setLegacyText(e.target.value)}
            placeholder="粘贴技术文章、面经等内容..."
            rows={10}
          />
          <Button loading={legacyLoading} onClick={handleLegacyText}>提取知识点</Button>
        </div>
      ),
    },
    {
      key: 'url',
      label: <span><LinkOutlined /> URL 导入</span>,
      children: (
        <div className="space-y-4">
          <Text type="secondary">输入网页 URL，自动抓取内容并提取知识点</Text>
          <Input
            value={legacyUrl}
            onChange={(e) => setLegacyUrl(e.target.value)}
            placeholder="https://example.com/article"
            onPressEnter={handleLegacyUrl}
          />
          <Button loading={legacyLoading} onClick={handleLegacyUrl}>抓取并提取</Button>
        </div>
      ),
    },
    {
      key: 'code',
      label: <span><CodeOutlined /> 代码导入</span>,
      children: (
        <div className="space-y-4">
          <Text type="secondary">粘贴代码，提取技术知识点</Text>
          <div className="flex gap-2">
            <Select
              value={legacyLanguage}
              onChange={setLegacyLanguage}
              placeholder="语言"
              allowClear
              className="w-32"
              options={[
                { label: 'Java', value: 'java' },
                { label: 'Python', value: 'python' },
                { label: 'JavaScript', value: 'javascript' },
                { label: 'Go', value: 'go' },
                { label: 'SQL', value: 'sql' },
              ]}
            />
          </div>
          <TextArea
            value={legacyCode}
            onChange={(e) => setLegacyCode(e.target.value)}
            placeholder="粘贴代码..."
            rows={10}
            className="font-mono text-sm"
          />
          <Button loading={legacyLoading} onClick={handleLegacyCode}>提取知识点</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Title level={2} className="!mb-1">导入知识</Title>
        <Text type="secondary">批量导入八股文、笔记、代码等内容到知识库</Text>
      </div>

      <Card>
        <Tabs items={tabItems} defaultActiveKey="quick" />

        {/* 传统导入结果 */}
        {legacyResult && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <Text strong>提取结果：</Text>
            <div className="mt-2 space-y-2">
              {legacyResult.drafts.map((draft) => (
                <div key={draft.id} className="p-2 bg-white rounded border">
                  <Text strong>{draft.title}</Text>
                  <p className="text-sm text-gray-500 mt-1 mb-0 line-clamp-2">{draft.content}</p>
                </div>
              ))}
            </div>
            <Button
              type="primary"
              className="mt-3"
              onClick={async () => {
                await importApi.confirmImport(legacyResult.job.id)
                message.success('已确认导入')
                navigate('/notes')
              }}
            >
              确认导入 {legacyResult.drafts.length} 个知识点
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
