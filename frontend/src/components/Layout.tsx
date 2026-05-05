import React from 'react'
import { Layout as AntLayout, Menu, Avatar, Dropdown } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  FileTextOutlined,
  MailOutlined,
  CloudUploadOutlined,
  VideoCameraOutlined,
  LogoutOutlined,
  UserOutlined,
  AudioOutlined,
  PictureOutlined,
  ScissorOutlined,
  SwapOutlined,
  LinkOutlined,
  RocketOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '../store/authStore'

const { Header, Sider, Content } = AntLayout

const MainLayout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ]

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/tts',
      icon: <AudioOutlined />,
      label: '语音合成',
    },
    {
      key: '/subtitle',
      icon: <FileTextOutlined />,
      label: '字幕生成',
    },
    {
      key: '/image',
      icon: <PictureOutlined />,
      label: '图像处理',
    },
    {
      key: '/video-editor',
      icon: <ScissorOutlined />,
      label: '视频编辑',
    },
    {
      key: '/video-transition',
      icon: <SwapOutlined />,
      label: '视频转场',
    },
    {
      key: '/video-merge',
      icon: <LinkOutlined />,
      label: '视频合并',
    },
    {
      key: '/batch',
      icon: <RocketOutlined />,
      label: '综合处理',
    },
    {
      key: '/templates',
      icon: <FileTextOutlined />,
      label: '模板管理',
    },
    {
      key: '/email',
      icon: <MailOutlined />,
      label: '邮件发送',
    },
    {
      key: '/files',
      icon: <CloudUploadOutlined />,
      label: '文件持久化',
    },
    {
      key: '/comfyui',
      icon: <PictureOutlined />,
      label: 'ComfyUI',
    },
    {
      key: '/http',
      icon: <ApiOutlined />,
      label: 'HTTP集成',
    },
    {
      key: '/remotion',
      icon: <VideoCameraOutlined />,
      label: 'Remotion工作室',
    },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={200}>
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: 18,
            fontWeight: 'bold',
          }}
        >
          VD 服务
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <div />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                gap: 8,
              }}
            >
              <Avatar icon={<UserOutlined />} />
              <span>{user?.username || '用户'}</span>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px', overflow: 'auto' }}>
          <div
            style={{
              padding: 24,
              background: '#fff',
              borderRadius: 8,
              minHeight: 'calc(100vh - 112px)',
            }}
          >
            {children}
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  )
}

export default MainLayout