import { useState } from 'react'
import {
  Typography,
  Descriptions,
  Tag,
  Space,
  Button,
  Tabs,
  Card,
  Empty,
  Spin,
  Table,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
} from 'antd'
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import {
  useGetProjectQuery,
  useUpdateProjectMutation,
  useDeleteProjectMutation,
} from '@/services/projectsApi'
import { useListRunsQuery } from '@/services/runsApi'
import type { Run } from '@/types'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

const stateConfig = {
  running: { color: 'blue', icon: <PlayCircleOutlined /> },
  finished: { color: 'green', icon: <CheckCircleOutlined /> },
  crashed: { color: 'red', icon: <CloseCircleOutlined /> },
  killed: { color: 'orange', icon: <StopOutlined /> },
}

function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editForm] = Form.useForm()

  const { data: project, isLoading } = useGetProjectQuery(id!)
  const { data: runsData, isLoading: isLoadingRuns } = useListRunsQuery({
    projectId: id,
    page: 1,
    pageSize: 20,
  })
  const [updateProject, { isLoading: isUpdating }] = useUpdateProjectMutation()
  const [deleteProject, { isLoading: isDeleting }] = useDeleteProjectMutation()

  const handleEdit = () => {
    if (project) {
      editForm.setFieldsValue({
        name: project.name,
        description: project.description,
        visibility: project.visibility,
      })
    }
    setIsEditModalOpen(true)
  }

  const handleUpdate = async (values: any) => {
    if (!id) return
    try {
      await updateProject({ id, data: values }).unwrap()
      message.success('Project updated successfully!')
      setIsEditModalOpen(false)
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to update project')
    }
  }

  const handleDelete = async () => {
    if (!id) return
    try {
      await deleteProject(id).unwrap()
      message.success('Project deleted successfully!')
      navigate('/projects')
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to delete project')
    }
  }

  const runsColumns: ColumnsType<Run> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/runs/${record.id}`)}>
          {text || `Run ${record.id.substring(0, 8)}`}
        </a>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => {
        const config = stateConfig[state as keyof typeof stateConfig]
        return (
          <Tag color={config.color} icon={config.icon}>
            {state.toUpperCase()}
          </Tag>
        )
      },
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) =>
        tags?.length > 0 ? (
          <Space size={4} wrap>
            {tags.slice(0, 3).map(tag => (
              <Tag key={tag}>{tag}</Tag>
            ))}
            {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
          </Space>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: 'Started At',
      dataIndex: 'startedAt',
      key: 'startedAt',
      render: (date: string) => dayjs(date).fromNow(),
    },
    {
      title: 'Duration',
      key: 'duration',
      render: (_, record) => {
        const duration = record.finishedAt
          ? dayjs(record.finishedAt).diff(dayjs(record.startedAt), 'second')
          : dayjs().diff(dayjs(record.startedAt), 'second')
        const hours = Math.floor(duration / 3600)
        const minutes = Math.floor((duration % 3600) / 60)
        const seconds = duration % 60
        if (hours > 0) return `${hours}h ${minutes}m`
        if (minutes > 0) return `${minutes}m ${seconds}s`
        return `${seconds}s`
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/runs/${record.id}`)}
        >
          View
        </Button>
      ),
    },
  ]

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!project) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="Project not found" />
      </div>
    )
  }

  // Calculate statistics
  const runs = runsData?.data || []
  const runningCount = runs.filter(r => r.state === 'running').length
  const finishedCount = runs.filter(r => r.state === 'finished').length
  const crashedCount = runs.filter(r => r.state === 'crashed').length

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/projects')}
          style={{ marginBottom: 16 }}
        >
          Back to Projects
        </Button>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <Title level={2} style={{ marginBottom: 8 }}>
              {project.name}
            </Title>
            <Space size={8}>
              <Tag
                color={project.visibility === 'public' ? 'green' : 'default'}
              >
                {project.visibility.toUpperCase()}
              </Tag>
              {project.description && (
                <Text type="secondary">{project.description}</Text>
              )}
            </Space>
          </div>
          <Space>
            <Button icon={<EditOutlined />} onClick={handleEdit}>
              Edit
            </Button>
            <Popconfirm
              title="Delete Project"
              description="Are you sure you want to delete this project? All runs and data will be lost."
              onConfirm={handleDelete}
              okText="Yes"
              cancelText="No"
              okButtonProps={{ danger: true }}
            >
              <Button
                icon={<DeleteOutlined />}
                danger
                loading={isDeleting}
              >
                Delete
              </Button>
            </Popconfirm>
          </Space>
        </div>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Runs"
              value={project.runCount || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Running"
              value={runningCount}
              valueStyle={{ color: '#1890ff' }}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Finished"
              value={finishedCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Crashed"
              value={crashedCount}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'overview',
            label: 'Overview',
            children: (
              <Card>
                <Descriptions title="Project Information" column={2} bordered>
                  <Descriptions.Item label="Project ID" span={2}>
                    <Text code copyable>
                      {project.id}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Name">
                    {project.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="Slug">
                    <Text code>{project.slug}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Visibility">
                    <Tag
                      color={
                        project.visibility === 'public' ? 'green' : 'default'
                      }
                    >
                      {project.visibility.toUpperCase()}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Run Count">
                    {project.runCount || 0}
                  </Descriptions.Item>
                  <Descriptions.Item label="Description" span={2}>
                    {project.description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Created At">
                    {dayjs(project.createdAt).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Updated At">
                    {dayjs(project.updatedAt).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Last Activity">
                    {project.lastActivity
                      ? dayjs(project.lastActivity).fromNow()
                      : 'No activity'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'runs',
            label: `Runs (${runs.length})`,
            children: (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => navigate('/runs')}
                  >
                    Create New Run
                  </Button>
                </div>
                <Table
                  columns={runsColumns}
                  dataSource={runs}
                  rowKey="id"
                  loading={isLoadingRuns}
                  pagination={{
                    total: runsData?.meta.total || 0,
                    pageSize: runsData?.meta.pageSize || 20,
                    current: runsData?.meta.page || 1,
                    showTotal: total => `Total ${total} runs`,
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'artifacts',
            label: 'Artifacts',
            children: (
              <Card>
                <Empty description="Artifacts for this project will be shown here" />
              </Card>
            ),
          },
          {
            key: 'sweeps',
            label: 'Sweeps',
            children: (
              <Card>
                <Empty description="Hyperparameter sweeps for this project will be shown here" />
              </Card>
            ),
          },
        ]}
      />

      {/* Edit Modal */}
      <Modal
        title="Edit Project"
        open={isEditModalOpen}
        onOk={() => editForm.submit()}
        onCancel={() => {
          editForm.resetFields()
          setIsEditModalOpen(false)
        }}
        confirmLoading={isUpdating}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdate}
          autoComplete="off"
        >
          <Form.Item
            name="name"
            label="Project Name"
            rules={[
              { required: true, message: 'Please input project name!' },
              { min: 3, message: 'Name must be at least 3 characters!' },
            ]}
          >
            <Input placeholder="my-awesome-project" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea
              rows={3}
              placeholder="Brief description of your project"
            />
          </Form.Item>

          <Form.Item
            name="visibility"
            label="Visibility"
            rules={[{ required: true }]}
          >
            <Select>
              <Select.Option value="private">Private</Select.Option>
              <Select.Option value="public">Public</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ProjectDetailPage
