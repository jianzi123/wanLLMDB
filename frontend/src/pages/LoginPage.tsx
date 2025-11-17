import { Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useLoginMutation, useGetMeQuery, authApi } from '@/services/authApi'
import { setCredentials } from '@features/auth/authSlice'
import { useAppDispatch, useAppStore } from '@/store/hooks'
import type { LoginFormData, User, AuthTokens } from '@/types'

const { Title, Text } = Typography

function LoginPage() {
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [login, { isLoading }] = useLoginMutation()

  const store = useAppStore()
  
  const onFinish = async (values: LoginFormData) => {
    try {
      // RTK Query will automatically transform snake_case to camelCase
      const tokens = await login(values).unwrap()

      // Validate token exists
      if (!tokens.accessToken) {
        console.error('Login response:', tokens)
        throw new Error('No access token received from server')
      }

      // Store tokens first so API calls can use them
      dispatch(setCredentials({ user: null as any, tokens }))

      // Get user info after login
      // Wait a bit for Redux state to update, then fetch user info
      let user: User | null = null
      try {
        // Small delay to ensure Redux state is updated
        await new Promise(resolve => setTimeout(resolve, 100))
        
        // Try using RTK Query first (it will use the token from Redux state)
        try {
          const result = await store.dispatch(
            authApi.endpoints.getMe.initiate(undefined, {
              forceRefetch: true,
            })
          )
          
          if (authApi.endpoints.getMe.matchFulfilled(result)) {
            user = result.data
            dispatch(setCredentials({ user, tokens }))
          } else {
            throw new Error('RTK Query getMe failed')
          }
        } catch (rtkError) {
          // Fallback to direct fetch with explicit token
          if (!tokens.accessToken) {
            console.error('RTK Query failed and no access token available')
            throw new Error('No access token available')
          }
          
          console.log('RTK Query failed, trying direct fetch with token:', tokens.accessToken.substring(0, 20) + '...')
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${tokens.accessToken}`,
              'Content-Type': 'application/json',
            },
          })
          
          if (response.ok) {
            user = await response.json()
            dispatch(setCredentials({ user, tokens }))
          } else {
            const errorText = await response.text()
            console.error('Failed to fetch user info:', response.status, response.statusText, errorText)
            // Use minimal user info as fallback
            user = { id: '', username: values.username, email: '', isActive: true, createdAt: new Date().toISOString() } as User
            dispatch(setCredentials({ user, tokens }))
          }
        }
      } catch (error) {
        console.error('Failed to fetch user info:', error)
        // Store tokens even if getMe fails
        user = { id: '', username: values.username, email: '', isActive: true, createdAt: new Date().toISOString() } as User
        dispatch(setCredentials({ user, tokens }))
      }

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
