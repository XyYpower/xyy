import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Button, Tooltip, Space } from 'antd'
import {
  BoldOutlined,
  ItalicOutlined,
  CodeOutlined,
  LinkOutlined,
  OrderedListOutlined,
} from '@ant-design/icons'
import 'highlight.js/styles/github.css'

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  minHeight?: string
}

type ViewMode = 'edit' | 'preview' | 'split'

const toolbarActions = [
  { icon: <BoldOutlined />, label: '粗体', before: '**', after: '**' },
  { icon: <ItalicOutlined />, label: '斜体', before: '*', after: '*' },
  { icon: <CodeOutlined />, label: '行内代码', before: '`', after: '`' },
  { icon: <LinkOutlined />, label: '链接', before: '[', after: '](url)' },
  { icon: <OrderedListOutlined />, label: '列表', before: '- ', after: '' },
  { label: 'H1', before: '# ', after: '' },
  { label: 'H2', before: '## ', after: '' },
  { label: '引用', before: '> ', after: '' },
  { label: '分割线', before: '\n---\n', after: '' },
  { icon: <CodeOutlined />, label: '代码块', before: '```\n', after: '\n```' },
]

export default function MarkdownEditor({ value, onChange, placeholder, minHeight = '60vh' }: MarkdownEditorProps) {
  const [mode, setMode] = useState<ViewMode>('split')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const insertMarkdown = (before: string, after: string = '') => {
    const textarea = textareaRef.current
    if (!textarea) return
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const selected = value.substring(start, end)
    const newValue = value.substring(0, start) + before + selected + after + value.substring(end)
    onChange(newValue)
    // 恢复光标位置
    setTimeout(() => {
      textarea.selectionStart = start + before.length
      textarea.selectionEnd = start + before.length + selected.length
      textarea.focus()
    }, 0)
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200 bg-gray-50">
        <Space size={4} wrap>
          {toolbarActions.map((action, i) => (
            <Tooltip key={i} title={action.label}>
              <Button
                type="text"
                size="small"
                icon={action.icon || undefined}
                onClick={() => insertMarkdown(action.before, action.after)}
              >
                {!action.icon && action.label}
              </Button>
            </Tooltip>
          ))}
        </Space>
        <Space size={4}>
          <Button size="small" type={mode === 'edit' ? 'primary' : 'text'} onClick={() => setMode('edit')}>编辑</Button>
          <Button size="small" type={mode === 'split' ? 'primary' : 'text'} onClick={() => setMode('split')}>分屏</Button>
          <Button size="small" type={mode === 'preview' ? 'primary' : 'text'} onClick={() => setMode('preview')}>预览</Button>
        </Space>
      </div>

      {/* 内容区 */}
      <div className="flex" style={{ minHeight }}>
        {(mode === 'edit' || mode === 'split') && (
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={`p-4 w-full resize-y font-mono text-sm focus:outline-none border-none ${mode === 'split' ? 'border-r border-gray-200' : ''}`}
            style={{ minHeight, resize: 'vertical' }}
          />
        )}
        {(mode === 'preview' || mode === 'split') && (
          <div
            className={`p-4 overflow-auto prose prose-sm max-w-none ${mode === 'split' ? 'border-l border-gray-200 w-1/2' : 'w-full'}`}
            style={{ minHeight }}
          >
            {value ? (
              <ReactMarkdown rehypePlugins={[rehypeHighlight]} remarkPlugins={[remarkGfm]}>
                {value}
              </ReactMarkdown>
            ) : (
              <span className="text-gray-400">暂无内容</span>
            )}
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      <div className="flex items-center justify-between px-3 py-1 border-t border-gray-200 bg-gray-50 text-xs text-gray-400">
        <span>{mode === 'edit' ? '编辑模式' : mode === 'preview' ? '预览模式' : '分屏模式'}</span>
        <span>{value.length} 字符</span>
      </div>
    </div>
  )
}
