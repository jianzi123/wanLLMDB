import { useState } from 'react'
import {
  Typography,
  Card,
  Descriptions,
  Avatar,
  Space,
  Button,
  Spin,
  Empty,
  Form,
  Input,
  message,
} from 'antd'
import {
  UserOutlined,
  MailOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import { useGetMeQuery } from '@/services/authApi'
import dayjs from 'dayjs'

const { Title, Text } = Typography

function ProfilePage() {
  const { data: user, isLoading } = useGetMeQuery()
  const [isEditing, setIsEditing] = useState(false)
  const [form] = Form.useForm()

  const handleEdit = () => {
    if (user) {
      form.setFieldsValue({
        fullName: user.fullName,
        email: user.email,
      })
    }
    setIsEditing(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      // TODO: Implement update user API
      console.log('Update user:', values)
      message.info('User update API not yet implemented')
      setIsEditing(false)
    } catch (error) {
      console.error('Validation failed:', error)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    form.resetFields()
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="User not found" />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>User Profile</Title>
        <Text type="secondary">Manage your personal information</Text>
      </div>

      {/* Profile Card */}
      <Card>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: 24,
          }}
        >
          <Space size={16} align="start">
            <Avatar
              size={80}
              icon={<UserOutlined />}
              src={user.avatarUrl}
              style={{ backgroundColor: '#1890ff' }}
            />
            <div>
              <Title level={4} style={{ margin: 0 }}>
                {user.fullName || user.username}
              </Title>
              <Text type="secondary">@{user.username}</Text>
              <br />
              <Space style={{ marginTop: 8 }}>
                <MailOutlined />
                <Text>{user.email}</Text>
              </Space>
            </div>
          </Space>
          {!isEditing && (
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEdit}
            >
              Edit Profile
            </Button>
          )}
        </div>

        {isEditing ? (
          <div>
            <Form form={form} layout="vertical">
              <Form.Item
                label="Full Name"
                name="fullName"
                rules={[
                  { required: false },
                  { max: 100, message: 'Name is too long' },
                ]}
              >
                <Input placeholder="Enter your full name" />
              </Form.Item>
              <Form.Item
                label="Email"
                name="email"
                rules={[
                  { required: true, message: 'Email is required' },
                  { type: 'email', message: 'Invalid email format' },
                ]}
              >
                <Input placeholder="Enter your email" />
              </Form.Item>
            </Form>
            <Space>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
              >
                Save Changes
              </Button>
              <Button icon={<CloseOutlined />} onClick={handleCancel}>
                Cancel
              </Button>
            </Space>
          </div>
        ) : (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="User ID">
              <Text code copyable>
                {user.id}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Username">
              {user.username}
            </Descriptions.Item>
            <Descriptions.Item label="Full Name">
              {user.fullName || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Email">{user.email}</Descriptions.Item>
            <Descriptions.Item label="Account Status">
              {user.isActive ? (
                <Text type="success">Active</Text>
              ) : (
                <Text type="danger">Inactive</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Member Since">
              {dayjs(user.createdAt).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* Statistics Card */}
      <Card title="Activity Statistics" style={{ marginTop: 24 }}>
        <Descriptions column={2}>
          <Descriptions.Item label="Total Projects">
            {/* TODO: Fetch user's project count */}
            <Text type="secondary">Coming soon</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Total Runs">
            {/* TODO: Fetch user's run count */}
            <Text type="secondary">Coming soon</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Active Runs">
            {/* TODO: Fetch user's active run count */}
            <Text type="secondary">Coming soon</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Total Artifacts">
            {/* TODO: Fetch user's artifact count */}
            <Text type="secondary">Coming soon</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

export default ProfilePage
