import { Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useRegisterMutation } from '@/services/authApi'
import type { RegisterFormData } from '@/types'

const { Title, Text } = Typography

function RegisterPage() {
  const navigate = useNavigate()
  const [register, { isLoading }] = useRegisterMutation()

  const onFinish = async (values: RegisterFormData) => {
    try {
      await register({
        username: values.username,
        email: values.email,
        password: values.password,
        fullName: values.fullName,
      }).unwrap()

      message.success('Registration successful! Please log in.')
      navigate('/login')
    } catch (error: any) {
      // Extract detailed error message from Pydantic validation errors
      let errorMessage = 'Registration failed. Please try again.'
      
      console.error('Registration error:', error)
      
      if (error?.data) {
        if (typeof error.data.detail === 'string') {
          // Single error message
          errorMessage = error.data.detail
        } else if (Array.isArray(error.data.detail)) {
          // Pydantic validation errors (array format)
          const errors = error.data.detail.map((err: any) => {
            const field = err.loc?.join('.') || 'field'
            const msg = err.msg || 'Invalid value'
            return `${field}: ${msg}`
          }).join('; ')
          errorMessage = errors || errorMessage
        } else if (error.data.detail) {
          // Try to stringify if it's an object
          errorMessage = JSON.stringify(error.data.detail)
        }
      } else if (error?.error) {
        // RTK Query error format
        errorMessage = error.error || errorMessage
      }
      
      message.error(errorMessage)
    }
  }

  return (
    <>
      <Title level={3} style={{ marginBottom: 24, textAlign: 'center' }}>
        Create Account
      </Title>
      <Form name="register" onFinish={onFinish} autoComplete="off" size="large">
        <Form.Item
          name="username"
          rules={[
            { required: true, message: 'Please input your username!' },
            { min: 3, message: 'Username must be at least 3 characters!' },
          ]}
        >
          <Input prefix={<UserOutlined />} placeholder="Username" />
        </Form.Item>

        <Form.Item
          name="email"
          rules={[
            { required: true, message: 'Please input your email!' },
            { type: 'email', message: 'Please input a valid email!' },
          ]}
        >
          <Input prefix={<MailOutlined />} placeholder="Email" />
        </Form.Item>

        <Form.Item
          name="fullName"
          rules={[
            { required: false },
            { max: 255, message: 'Full name must be less than 255 characters!' },
          ]}
        >
          <Input prefix={<UserOutlined />} placeholder="Full Name (Optional)" />
        </Form.Item>

        <Form.Item
          name="password"
          rules={[
            { required: true, message: 'Please input your password!' },
            { min: 12, message: 'Password must be at least 12 characters!' },
            { max: 60, message: 'Password cannot exceed 60 characters!' },
            {
              pattern: /[A-Z]/,
              message: 'Password must contain at least one uppercase letter!',
            },
            {
              pattern: /[a-z]/,
              message: 'Password must contain at least one lowercase letter!',
            },
            {
              pattern: /\d/,
              message: 'Password must contain at least one number!',
            },
            {
              pattern: /[!@#$%^&*(),.?":{}|<>]/,
              message: 'Password must contain at least one special character!',
            },
          ]}
          help="Password must be 12-60 characters with uppercase, lowercase, number, and special character"
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Password" />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          dependencies={['password']}
          rules={[
            { required: true, message: 'Please confirm your password!' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve()
                }
                return Promise.reject(new Error('Passwords do not match!'))
              },
            }),
          ]}
        >
          <Input.Password prefix={<LockOutlined />} placeholder="Confirm Password" />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={isLoading}>
            Sign Up
          </Button>
        </Form.Item>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            Already have an account? <Link to="/login">Sign in</Link>
          </Text>
        </div>
      </Form>
    </>
  )
}

export default RegisterPage
