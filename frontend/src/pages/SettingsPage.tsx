import { useState } from 'react'
import {
  Typography,
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Switch,
  Divider,
  Space,
  message,
  Modal,
  Alert,
} from 'antd'
import {
  LockOutlined,
  BellOutlined,
  SettingOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useGetMeQuery } from '@/services/authApi'

const { Title, Text, Paragraph } = Typography

function SettingsPage() {
  const { data: user } = useGetMeQuery()
  const [passwordForm] = Form.useForm()
  const [notificationForm] = Form.useForm()
  const [preferencesForm] = Form.useForm()

  // State for notification settings
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [runCompletionNotif, setRunCompletionNotif] = useState(true)
  const [runFailureNotif, setRunFailureNotif] = useState(true)
  const [weeklyDigest, setWeeklyDigest] = useState(false)

  // State for preferences
  const [darkMode, setDarkMode] = useState(false)
  const [compactView, setCompactView] = useState(false)

  const handleChangePassword = async () => {
    try {
      const values = await passwordForm.validateFields()
      // TODO: Implement change password API
      console.log('Change password:', values)
      message.info('Password change API not yet implemented')
      passwordForm.resetFields()
    } catch (error) {
      console.error('Validation failed:', error)
    }
  }

  const handleSaveNotifications = () => {
    // TODO: Implement save notification settings API
    message.success('Notification settings saved successfully!')
  }

  const handleSavePreferences = () => {
    // TODO: Implement save preferences API
    message.success('Preferences saved successfully!')
  }

  const handleDeleteAccount = () => {
    Modal.confirm({
      title: 'Delete Account',
      icon: <ExclamationCircleOutlined />,
      content:
        'Are you sure you want to delete your account? This action cannot be undone. All your projects, runs, and data will be permanently deleted.',
      okText: 'Delete Account',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk() {
        // TODO: Implement delete account API
        message.info('Account deletion API not yet implemented')
      },
    })
  }

  const tabItems = [
    {
      key: 'security',
      label: (
        <span>
          <LockOutlined />
          Security
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>Change Password</Title>
          <Paragraph type="secondary">
            Update your password to keep your account secure
          </Paragraph>
          <Form
            form={passwordForm}
            layout="vertical"
            style={{ maxWidth: 500 }}
          >
            <Form.Item
              label="Current Password"
              name="currentPassword"
              rules={[
                { required: true, message: 'Please enter current password' },
              ]}
            >
              <Input.Password placeholder="Enter current password" />
            </Form.Item>
            <Form.Item
              label="New Password"
              name="newPassword"
              rules={[
                { required: true, message: 'Please enter new password' },
                { min: 8, message: 'Password must be at least 8 characters' },
              ]}
            >
              <Input.Password placeholder="Enter new password" />
            </Form.Item>
            <Form.Item
              label="Confirm New Password"
              name="confirmPassword"
              dependencies={['newPassword']}
              rules={[
                { required: true, message: 'Please confirm new password' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('newPassword') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(
                      new Error('Passwords do not match')
                    )
                  },
                }),
              ]}
            >
              <Input.Password placeholder="Confirm new password" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" onClick={handleChangePassword}>
                Change Password
              </Button>
            </Form.Item>
          </Form>

          <Divider />

          <Title level={4}>Two-Factor Authentication</Title>
          <Paragraph type="secondary">
            Add an extra layer of security to your account
          </Paragraph>
          <Alert
            message="Coming Soon"
            description="Two-factor authentication will be available in a future update."
            type="info"
            showIcon
          />

          <Divider />

          <Title level={4}>Danger Zone</Title>
          <Alert
            message="Delete Account"
            description="Once you delete your account, there is no going back. Please be certain."
            type="error"
            showIcon
            action={
              <Button size="small" danger onClick={handleDeleteAccount}>
                Delete Account
              </Button>
            }
          />
        </Card>
      ),
    },
    {
      key: 'notifications',
      label: (
        <span>
          <BellOutlined />
          Notifications
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>Email Notifications</Title>
          <Paragraph type="secondary">
            Choose what you want to be notified about
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Email Notifications</Text>
                <br />
                <Text type="secondary">
                  Receive email notifications for your account activity
                </Text>
              </div>
              <Switch
                checked={emailNotifications}
                onChange={setEmailNotifications}
              />
            </div>

            <Divider style={{ margin: '8px 0' }} />

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Run Completion</Text>
                <br />
                <Text type="secondary">
                  Notify when your training runs complete successfully
                </Text>
              </div>
              <Switch
                checked={runCompletionNotif}
                onChange={setRunCompletionNotif}
                disabled={!emailNotifications}
              />
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Run Failure</Text>
                <br />
                <Text type="secondary">
                  Notify when your training runs crash or fail
                </Text>
              </div>
              <Switch
                checked={runFailureNotif}
                onChange={setRunFailureNotif}
                disabled={!emailNotifications}
              />
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Weekly Digest</Text>
                <br />
                <Text type="secondary">
                  Receive a weekly summary of your activity
                </Text>
              </div>
              <Switch
                checked={weeklyDigest}
                onChange={setWeeklyDigest}
                disabled={!emailNotifications}
              />
            </div>

            <Divider />

            <Button type="primary" onClick={handleSaveNotifications}>
              Save Notification Settings
            </Button>
          </Space>
        </Card>
      ),
    },
    {
      key: 'preferences',
      label: (
        <span>
          <SettingOutlined />
          Preferences
        </span>
      ),
      children: (
        <Card>
          <Title level={4}>Display Preferences</Title>
          <Paragraph type="secondary">
            Customize how the application looks and feels
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Dark Mode</Text>
                <br />
                <Text type="secondary">
                  Use dark theme for the application
                </Text>
              </div>
              <Switch checked={darkMode} onChange={setDarkMode} />
            </div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <Text strong>Compact View</Text>
                <br />
                <Text type="secondary">
                  Use a more compact layout for lists and tables
                </Text>
              </div>
              <Switch checked={compactView} onChange={setCompactView} />
            </div>

            <Divider />

            <Alert
              message="Coming Soon"
              description="Display preferences will be fully functional in a future update. Currently, changes are not persisted."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Button type="primary" onClick={handleSavePreferences}>
              Save Preferences
            </Button>
          </Space>
        </Card>
      ),
    },
  ]

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>Settings</Title>
        <Text type="secondary">
          Manage your account settings and preferences
        </Text>
      </div>

      <Tabs defaultActiveKey="security" items={tabItems} />
    </div>
  )
}

export default SettingsPage
