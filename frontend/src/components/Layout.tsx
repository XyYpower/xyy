import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu } from 'antd'
import {
  BookOutlined,
  MessageOutlined,
  HomeOutlined,
} from '@ant-design/icons'

const { Sider, Content } = AntLayout

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: '概览' },
  { key: '/notes', icon: <BookOutlined />, label: '笔记' },
  { key: '/chat', icon: <MessageOutlined />, label: 'AI 对话' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selectedKey = menuItems.find(
    (item) => location.pathname === item.key || (item.key !== '/' && location.pathname.startsWith(item.key))
  )?.key || '/'

  return (
    <AntLayout className="min-h-screen">
      <Sider width={200} theme="light" className="border-r border-gray-200">
        <div className="h-16 flex items-center justify-center border-b border-gray-200">
          <h1 className="text-xl font-bold text-indigo-600 m-0">KnowBase</h1>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="border-none"
        />
      </Sider>
      <AntLayout>
        <Content className="p-6 bg-gray-50">
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
