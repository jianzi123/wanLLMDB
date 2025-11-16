import { Form, Input, Button, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import type { LoginFormData } from '@/types'

const { Title, Text } = Typography

function LoginPage() {
  const navigate = useNavigate()

  const onFinish = (values: LoginFormData) => {
    console.log('Login:', values)
    // TODO: Implement login logic
    navigate('/dashboard')
  }

  return (
    <>
      <Title level={3} style={{ marginBottom: 24, textAlign: 'center' }}>
        Sign In
      </Title>
      <Form
        name="login"
        initialValues={{ remember: true }}
        onFinish={onFinish}
        autoComplete="off"
        size="large"
      >
        <Form.Item
          name="username"
          rules={[{ required: true, message: 'Please input your username!' }]}
        >
          <Input prefix={<UserOutlined />} placeholder="Username" />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[{ required: true, message: 'Please input your password!' }]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Password" />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block>
            Sign In
          </Button>
        </Form.Item>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            Don&apos;t have an account? <Link to="/register">Sign up</Link>
          </Text>
        </div>
      </Form>
    </>
  )
}

export default LoginPage
