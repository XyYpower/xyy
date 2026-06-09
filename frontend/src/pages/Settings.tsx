import { useState, useEffect } from 'react'
import { Button, Switch, TimePicker, Input, Typography, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { downloadExport } from '../api/export'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'

const { Title, Text } = Typography

export default function Settings() {
  const user = useAuthStore((state) => state.user)
  const loadMe = useAuthStore((state) => state.loadMe)

  // 邮箱
  const [email, setEmail] = useState(user?.email || '')
  const [savingEmail, setSavingEmail] = useState(false)

  // 密码
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [savingPassword, setSavingPassword] = useState(false)

  // 提醒
  const [reminderEnabled, setReminderEnabled] = useState(user?.reminder_enabled ?? false)
  const [reminderTime, setReminderTime] = useState<string | null>(user?.reminder_time?.slice(0, 5) || null)
  const [savingReminder, setSavingReminder] = useState(false)

  useEffect(() => {
    if (user) {
      setEmail(user.email || '')
      setReminderEnabled(user.reminder_enabled)
      setReminderTime(user.reminder_time?.slice(0, 5) || null)
    }
  }, [user])

  const handleSaveEmail = async () => {
    setSavingEmail(true)
    try {
      await authApi.updateProfile({ email: email || undefined })
      await loadMe()
      message.success('邮箱已更新')
    } catch {
      message.error('更新失败')
    } finally {
      setSavingEmail(false)
    }
  }

  const handleChangePassword = async () => {
    if (!oldPassword || !newPassword) {
      message.warning('请填写密码')
      return
    }
    if (newPassword !== confirmPassword) {
      message.warning('两次输入的新密码不一致')
      return
    }
    if (newPassword.length < 6) {
      message.warning('新密码至少 6 位')
      return
    }
    setSavingPassword(true)
    try {
      await authApi.changePassword({ old_password: oldPassword, new_password: newPassword })
      message.success('密码已修改')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch {
      message.error('修改失败，请检查旧密码是否正确')
    } finally {
      setSavingPassword(false)
    }
  }

  const handleSaveReminder = async () => {
    setSavingReminder(true)
    try {
      await authApi.updateProfile({
        reminder_enabled: reminderEnabled,
        reminder_time: reminderEnabled ? (reminderTime || '09:00') : undefined,
      })
      await loadMe()
      message.success('提醒设置已更新')
    } catch {
      message.error('更新失败')
    } finally {
      setSavingReminder(false)
    }
  }

  const exportData = async (type: 'json' | 'markdown' | 'anki') => {
    try {
      await downloadExport(type)
      message.success('导出已开始')
    } catch {
      message.error('导出失败')
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <Title level={2} className="!mb-1">设置</Title>
        <Text type="secondary">管理账号信息、提醒和数据导出</Text>
      </div>

      <div className="space-y-4">
        {/* 账号信息 */}
        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>账号信息</Title>
          <div className="space-y-3 mt-3">
            <div>
              <Text type="secondary" className="text-sm">用户名</Text>
              <div className="text-base font-medium">{user?.username ?? '-'}</div>
            </div>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Text type="secondary" className="text-sm">邮箱</Text>
                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="设置邮箱地址"
                />
              </div>
              <Button loading={savingEmail} onClick={handleSaveEmail}>保存</Button>
            </div>
          </div>
        </section>

        {/* 修改密码 */}
        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>修改密码</Title>
          <div className="space-y-3 mt-3">
            <Input.Password
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="当前密码"
            />
            <Input.Password
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="新密码（至少 6 位）"
            />
            <Input.Password
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="确认新密码"
            />
            <Button loading={savingPassword} onClick={handleChangePassword}>修改密码</Button>
          </div>
        </section>

        {/* 复习提醒 */}
        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>复习提醒</Title>
          <div className="flex items-center gap-4 mt-3">
            <Switch
              checked={reminderEnabled}
              onChange={setReminderEnabled}
            />
            <Text>开启每日提醒</Text>
          </div>
          <div className="flex items-end gap-3 mt-3">
            <div className="flex-1">
              <Text type="secondary" className="text-sm">提醒时间</Text>
              <TimePicker
                value={reminderTime ? dayjs(reminderTime, 'HH:mm') : null}
                format="HH:mm"
                className="w-full"
                disabled={!reminderEnabled}
                onChange={(time) => setReminderTime(time ? time.format('HH:mm') : null)}
              />
            </div>
            <Button loading={savingReminder} onClick={handleSaveReminder}>保存</Button>
          </div>
        </section>

        {/* 数据导出 */}
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

        {/* MCP Server */}
        <section className="bg-white border border-gray-200 rounded-lg p-5">
          <Title level={4}>MCP Server</Title>
          <Text type="secondary">
            KnowBase 支持 MCP（Model Context Protocol），可以让 Claude Desktop、Cursor 等 AI 工具直接访问你的知识库。
          </Text>
          <div className="mt-3 space-y-2">
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
              <Text strong className="text-yellow-700">默认关闭</Text>
              <div className="text-yellow-600 mt-1">
                MCP 需要在环境变量中显式启用。在 <code>.env</code> 文件中配置：
              </div>
              <div className="bg-gray-800 text-green-400 rounded p-2 mt-2 font-mono text-xs">
                KNOWBASE_MCP_ENABLED=true<br/>
                KNOWBASE_MCP_USER_ID=你的用户ID<br/>
                KNOWBASE_MCP_TOKEN=你的访问令牌
              </div>
            </div>
            <div className="text-sm text-gray-500">
              <p className="mb-1"><strong>启用后可用工具：</strong></p>
              <ul className="list-disc list-inside space-y-1">
                <li><code>search_notes</code> — 搜索知识点</li>
                <li><code>get_note</code> — 获取知识点详情</li>
                <li><code>create_note_draft</code> — 创建知识点草稿</li>
                <li><code>get_review_cards</code> — 获取今日复习卡片</li>
                <li><code>generate_interview_questions</code> — 生成面试题</li>
              </ul>
              <p className="mt-2 mb-1"><strong>可用资源：</strong></p>
              <ul className="list-disc list-inside space-y-1">
                <li><code>knowbase://notes/{"{id}"}</code> — 知识点内容</li>
                <li><code>knowbase://reviews/today</code> — 今日复习</li>
                <li><code>knowbase://paths</code> — 学习路径</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
