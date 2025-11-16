import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Space, Typography } from 'antd'
import type { MenuProps } from 'antd'
import {
  DashboardOutlined,
  FolderOutlined,
  ExperimentOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  RocketOutlined,
} from '@ant-design/icons'
import { useAppSelector, useAppDispatch } from '@/store/hooks'
import { logout } from '@features/auth/authSlice'

const { Header, Sider, Content } = Layout
const { Text } = Typography

function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const dispatch = useAppDispatch()
  const user = useAppSelector(state => state.auth.user)

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/projects',
      icon: <FolderOutlined />,
      label: 'Projects',
    },
    {
      key: '/runs',
      icon: <ExperimentOutlined />,
      label: 'Runs',
    },
    {
      key: '/sweeps',
      icon: <ThunderboltOutlined />,
      label: 'Sweeps',
    },
    {
      key: '/artifacts',
      icon: <DatabaseOutlined />,
      label: 'Artifacts',
    },
    {
      key: '/registry/models',
      icon: <RocketOutlined />,
      label: 'Model Registry',
    },
    {
      key: '/reports',
      icon: <FileTextOutlined />,
      label: 'Reports',
    },
  ]

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      danger: true,
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  // Determine selected menu item based on current path
  const getSelectedKey = () => {
    const path = location.pathname
    if (path.startsWith('/registry/models')) return '/registry/models'
    if (path.startsWith('/sweeps')) return '/sweeps'
    if (path.startsWith('/artifacts')) return '/artifacts'
    if (path.startsWith('/runs')) return '/runs'
    if (path.startsWith('/projects')) return '/projects'
    return path
  }

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      dispatch(logout())
      navigate('/login')
    } else if (key === 'profile') {
      navigate('/profile')
    } else if (key === 'settings') {
      navigate('/settings')
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="light"
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            fontWeight: 600,
            color: '#1890ff',
          }}
        >
          wanLLMDB
        </div>
        <Menu
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: 220 }}>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }}
        >
          <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenuClick }}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} src={user?.avatarUrl} />
              <Text>{user?.username || 'User'}</Text>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px', padding: '24px', background: '#fff' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
