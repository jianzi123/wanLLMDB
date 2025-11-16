import { useState } from 'react'
import {
  Typography,
  Button,
  Table,
  Space,
  Tag,
  Select,
  Input,
  Modal,
  Form,
  Popconfirm,
  message,
} from 'antd'
import {
  FileOutlined,
  DatabaseOutlined,
  CodeOutlined,
  FolderOutlined,
  SearchOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import type { Artifact, ArtifactType, ArtifactFormData } from '@/types'
import {
  useListArtifactsQuery,
  useCreateArtifactMutation,
  useDeleteArtifactMutation,
} from '@/services/artifactsApi'
import { useListProjectsQuery } from '@/services/projectsApi'

dayjs.extend(relativeTime)

const { Title } = Typography

const artifactTypeConfig = {
  model: { color: 'purple', icon: <DatabaseOutlined />, label: 'Model' },
  dataset: { color: 'blue', icon: <FolderOutlined />, label: 'Dataset' },
  file: { color: 'green', icon: <FileOutlined />, label: 'File' },
  code: { color: 'orange', icon: <CodeOutlined />, label: 'Code' },
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function ArtifactsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [typeFilter, setTypeFilter] = useState<ArtifactType | undefined>()
  const [search, setSearch] = useState<string>()
  const [projectFilter, setProjectFilter] = useState<string | undefined>(
    searchParams.get('project') || undefined
  )
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [form] = Form.useForm()

  const { data, isLoading } = useListArtifactsQuery({
    page,
    pageSize,
    artifactType: typeFilter,
    search,
    projectId: projectFilter,
  })

  const { data: projectsData } = useListProjectsQuery({ pageSize: 100 })
  const [createArtifact, { isLoading: isCreating }] = useCreateArtifactMutation()
  const [deleteArtifact] = useDeleteArtifactMutation()

  const columns: ColumnsType<Artifact> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/artifacts/${record.id}`)}>
          {text}
        </a>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: ArtifactType) => {
        const config = artifactTypeConfig[type]
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        )
      },
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <span style={{ color: '#999' }}>No description</span>,
    },
    {
      title: 'Versions',
      dataIndex: 'versionCount',
      key: 'versionCount',
      width: 100,
      align: 'center',
      render: (count: number, record) => (
        <Space direction="vertical" size={0}>
          <strong>{count}</strong>
          {record.latestVersion && (
            <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>
              {record.latestVersion}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) =>
        tags?.length > 0 ? (
          <Space size={4} wrap>
            {tags.slice(0, 3).map(tag => (
              <Tag key={tag} style={{ margin: 0 }}>
                {tag}
              </Tag>
            ))}
            {tags.length > 3 && (
              <Tag style={{ margin: 0 }}>+{tags.length - 3}</Tag>
            )}
          </Space>
        ) : (
          <span style={{ color: '#999' }}>No tags</span>
        ),
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => dayjs(date).fromNow(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/artifacts/${record.id}`)}
          >
            View
          </Button>
          <Popconfirm
            title="Delete artifact"
            description="Are you sure you want to delete this artifact? This will also delete all versions and files."
            onConfirm={async () => {
              try {
                await deleteArtifact(record.id).unwrap()
                message.success('Artifact deleted')
              } catch (error) {
                message.error('Failed to delete artifact')
              }
            }}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger size="small">
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleCreate = async (values: ArtifactFormData) => {
    try {
      const artifact = await createArtifact(values).unwrap()
      message.success('Artifact created successfully')
      setIsCreateModalOpen(false)
      form.resetFields()
      navigate(`/artifacts/${artifact.id}`)
    } catch (error) {
      message.error('Failed to create artifact')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>Artifacts</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsCreateModalOpen(true)}
        >
          New Artifact
        </Button>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="Search artifacts..."
          prefix={<SearchOutlined />}
          allowClear
          style={{ width: 250 }}
          onChange={e => setSearch(e.target.value || undefined)}
        />
        <Select
          placeholder="Filter by type"
          allowClear
          style={{ width: 150 }}
          onChange={setTypeFilter}
          options={Object.entries(artifactTypeConfig).map(([value, config]) => ({
            value,
            label: (
              <span>
                {config.icon} {config.label}
              </span>
            ),
          }))}
        />
        <Select
          placeholder="Filter by project"
          allowClear
          showSearch
          style={{ width: 200 }}
          value={projectFilter}
          onChange={(value) => {
            setProjectFilter(value)
            if (value) {
              setSearchParams({ project: value })
            } else {
              setSearchParams({})
            }
          }}
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={projectsData?.data.map(project => ({
            value: project.id,
            label: project.name,
          }))}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} artifacts`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize)
          },
        }}
      />

      <Modal
        title="Create New Artifact"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        confirmLoading={isCreating}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter artifact name' }]}
          >
            <Input placeholder="my-model" />
          </Form.Item>

          <Form.Item
            label="Type"
            name="type"
            rules={[{ required: true, message: 'Please select artifact type' }]}
          >
            <Select
              placeholder="Select type"
              options={Object.entries(artifactTypeConfig).map(([value, config]) => ({
                value,
                label: (
                  <span>
                    {config.icon} {config.label}
                  </span>
                ),
              }))}
            />
          </Form.Item>

          <Form.Item
            label="Project"
            name="projectId"
            rules={[{ required: true, message: 'Please select project' }]}
          >
            <Select
              placeholder="Select project"
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={projectsData?.data.map(project => ({
                value: project.id,
                label: project.name,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
          >
            <Input.TextArea
              rows={3}
              placeholder="Describe your artifact..."
            />
          </Form.Item>

          <Form.Item
            label="Tags"
            name="tags"
          >
            <Select
              mode="tags"
              placeholder="Add tags"
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ArtifactsPage
