import { useState } from 'react'
import {
  Typography,
  Button,
  Table,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import type { Project, ProjectFormData } from '@/types'
import {
  useListProjectsQuery,
  useCreateProjectMutation,
  useDeleteProjectMutation,
} from '@/services/projectsApi'

dayjs.extend(relativeTime)

const { Title } = Typography

function ProjectsPage() {
  const navigate = useNavigate()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form] = Form.useForm()

  // API hooks
  const { data, isLoading, refetch } = useListProjectsQuery({
    page: 1,
    pageSize: 20,
  })
  const [createProject, { isLoading: isCreating }] = useCreateProjectMutation()
  const [deleteProject] = useDeleteProjectMutation()

  const columns: ColumnsType<Project> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/projects/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Visibility',
      dataIndex: 'visibility',
      key: 'visibility',
      render: (visibility: string) => (
        <Tag color={visibility === 'public' ? 'green' : 'default'}>
          {visibility.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Runs',
      dataIndex: 'runCount',
      key: 'runCount',
      render: (count: number) => count || 0,
    },
    {
      title: 'Last Activity',
      dataIndex: 'lastActivity',
      key: 'lastActivity',
      render: (date: string) => (date ? dayjs(date).fromNow() : 'No activity'),
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Project) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/projects/${record.id}`)}
          >
            View
          </Button>
          <Popconfirm
            title="Delete project"
            description="Are you sure you want to delete this project?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" size="small" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleCreate = async (values: ProjectFormData) => {
    try {
      await createProject(values).unwrap()
      message.success('Project created successfully!')
      form.resetFields()
      setIsModalOpen(false)
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to create project')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteProject(id).unwrap()
      message.success('Project deleted successfully!')
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to delete project')
    }
  }

  return (
    <div>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}
      >
        <Title level={2}>Projects</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
        >
          New Project
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: data?.meta.total || 0,
          pageSize: data?.meta.pageSize || 20,
          current: data?.meta.page || 1,
          showSizeChanger: true,
          showTotal: total => `Total ${total} projects`,
        }}
      />

      <Modal
        title="Create New Project"
        open={isModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          form.resetFields()
          setIsModalOpen(false)
        }}
        confirmLoading={isCreating}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
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
            initialValue="private"
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

export default ProjectsPage
