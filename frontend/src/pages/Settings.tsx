import { Button, Switch, TimePicker, Typography, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { downloadExport } from '../api/export'
import { useAuthStore } from '../store/authStore'

const { Text, Title } = Typography

export default function Settings() {
  const user = useAuthStore((state) => state.user)

  const exportData = async (type: 'json' | 'markdown' | 'anki') => {
    try {
      await downloadExport(type)
      message.success('导出已开始')
    } catch {
      message.error('导出失败')
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <Title level={2} className="!mb-1">设置</Title>
        <Text type="secondary">管理导出、提醒和账号信息</Text>
      </div>

      <div className="space-y-4">
        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>数据导出</Title>
          <Text type="secondary">导出当前账号的知识点、复习卡片、学习路径和面试记录</Text>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button icon={<DownloadOutlined />} onClick={() => exportData('json')}>
              导出 JSON
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => exportData('markdown')}>
              导出 Markdown
            </Button>
            <Button icon={<DownloadOutlined />} onClick={() => exportData('anki')}>
              导出 Anki CSV
            </Button>
          </div>
        </section>

        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>复习提醒</Title>
          <div className="flex flex-wrap items-center gap-4 mt-3">
            <Switch disabled />
            <Text type="secondary">每日提醒后端接口将在账号设置增强阶段接入</Text>
            <TimePicker disabled format="HH:mm" />
          </div>
        </section>

        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>账号信息</Title>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <div>
              <div className="text-sm text-gray-500">用户名</div>
              <div className="text-lg font-medium">{user?.username ?? '当前用户'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">账号 ID</div>
              <div className="text-lg font-mono text-gray-700 truncate">{user?.id ?? '-'}</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
