import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Card, Form, Input, Typography, message } from 'antd'
import { useAuthStore } from '../store/authStore'

const { Title, Text } = Typography

export default function Register() {
  const navigate = useNavigate()
  const register = useAuthStore((state) => state.register)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await register(values.username, values.password)
      message.success('注册成功')
      navigate('/', { replace: true })
    } catch {
      message.error('注册失败，用户名可能已存在')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-sm">
        <Title level={3} className="!mb-1">创建账号</Title>
        <Text type="secondary">每个账号拥有独立知识点和复习数据</Text>
        <Form layout="vertical" onFinish={handleSubmit} className="mt-6">
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '至少 3 个字符' },
            ]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '至少 6 个字符' },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>注册并进入</Button>
        </Form>
        <div className="mt-4 text-center text-sm">
          已有账号？<Link to="/login">登录</Link>
        </div>
      </Card>
    </div>
  )
}

