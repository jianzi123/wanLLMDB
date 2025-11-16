import { Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useLoginMutation, useGetMeQuery } from '@/services/authApi'
import { setCredentials } from '@features/auth/authSlice'
import { useAppDispatch } from '@/store/hooks'
import type { LoginFormData } from '@/types'

const { Title, Text } = Typography

function LoginPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [login, { isLoading }] = useLoginMutation()

  const onFinish = async (values: LoginFormData) => {
    try {
      const tokens = await login(values).unwrap()

      // Store tokens
      dispatch(setCredentials({ user: null as any, tokens }))

      // Get user info
      // Note: We'll fetch this after login
      message.success('Login successful!')
      navigate('/dashboard')
    } catch (error: any) {
      message.error(error?.data?.detail || 'Login failed. Please try again.')
    }
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
          <Button type="primary" htmlType="submit" block loading={isLoading}>
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
