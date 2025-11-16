import { Outlet } from 'react-router-dom'
import { Layout, Typography } from 'antd'

const { Content } = Layout
const { Title } = Typography

function AuthLayout() {
  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <Title level={1} style={{ color: '#1890ff', marginBottom: 8 }}>
            wanLLMDB
          </Title>
          <Title level={4} type="secondary" style={{ fontWeight: 400 }}>
            ML Experiment Management Platform
          </Title>
        </div>
        <div
          style={{
            width: '100%',
            maxWidth: 400,
            padding: 32,
            background: '#fff',
            borderRadius: 8,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}
        >
          <Outlet />
        </div>
      </Content>
    </Layout>
  )
}

export default AuthLayout
