import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu } from 'antd'
import {
  BookOutlined,
  BranchesOutlined,
  ImportOutlined,
  MessageOutlined,
  HomeOutlined,
  LogoutOutlined,
  ScheduleOutlined,
  SettingOutlined,
  TrophyOutlined,
  DashboardOutlined,
} from '@ant-design/icons'
import { Button } from 'antd'
import { useAuthStore } from '../store/authStore'

const { Sider, Content } = AntLayout

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: '概览' },
  { key: '/notes', icon: <BookOutlined />, label: '知识点' },
  { key: '/chat', icon: <MessageOutlined />, label: 'AI 对话' },
  { key: '/review', icon: <ScheduleOutlined />, label: '间隔复习' },
  { key: '/interview', icon: <TrophyOutlined />, label: '模拟面试' },
  { key: '/import', icon: <ImportOutlined />, label: '导入知识' },
  { key: '/paths', icon: <BranchesOutlined />, label: '学习路径' },
  { key: '/traces', icon: <DashboardOutlined />, label: 'Trace Lab' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const selectedKey = menuItems.find(
    (item) => location.pathname === item.key || (item.key !== '/' && location.pathname.startsWith(item.key))
  )?.key || '/'

  return (
    <AntLayout className="min-h-screen">
      <Sider width={200} theme="light" className="border-r border-gray-200">
        <div className="h-full flex flex-col">
          <div className="h-16 flex items-center justify-center border-b border-gray-200">
            <h1 className="text-xl font-bold text-indigo-600 m-0">KnowBase</h1>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            className="border-none flex-1"
          />
          <div className="border-t border-gray-200 p-3">
            <div className="text-sm font-medium truncate mb-2">{user?.username || '当前用户'}</div>
            <Button
              block
              icon={<LogoutOutlined />}
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              退出
            </Button>
          </div>
        </div>
      </Sider>
      <AntLayout>
        <Content className="p-6 bg-gray-50">
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
