import { useState } from 'react'
import {
  Typography,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Card,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  message,
  Empty,
  Spin,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  useListModelsQuery,
  useGetRegistrySummaryQuery,
  useCreateModelMutation,
  type RegisteredModel,
  type RegisteredModelCreate,
  ModelStage,
} from '@/services/modelRegistryApi'

const { Title, Text } = Typography
const { Search } = Input

// Helper function to get stage color
const getStageColor = (stage: ModelStage): string => {
  switch (stage) {
    case ModelStage.PRODUCTION:
      return 'green'
    case ModelStage.STAGING:
      return 'blue'
    case ModelStage.ARCHIVED:
      return 'default'
    default:
      return 'orange'
  }
}

function ModelRegistryPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [form] = Form.useForm()

  // Fetch models
  const { data, isLoading, refetch } = useListModelsQuery({
    search,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  // Fetch summary
  const { data: summary } = useGetRegistrySummaryQuery(undefined)

  // Create model mutation
  const [createModel, { isLoading: isCreating }] = useCreateModelMutation()

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleCreateModel = async (values: any) => {
    try {
      // TODO: Get project ID from context or user selection
      const projectId = localStorage.getItem('currentProjectId') || ''

      await createModel({
        ...values,
        projectId,
        tags: values.tags ? values.tags.split(',').map((t: string) => t.trim()) : [],
      }).unwrap()

      message.success('Model registered successfully')
      setIsCreateModalOpen(false)
      form.resetFields()
      refetch()
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to register model')
    }
  }

  const columns: ColumnsType<RegisteredModel> = [
    {
      title: 'Model Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space direction="vertical" size={0}>
          <Button
            type="link"
            onClick={() => navigate(`/registry/models/${record.id}`)}
            style={{ padding: 0, height: 'auto' }}
          >
            <Text strong>{name}</Text>
          </Button>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
      width: '30%',
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: tags => (
        <Space size={4} wrap>
          {tags && tags.length > 0 ? (
            tags.map((tag: string) => <Tag key={tag}>{tag}</Tag>)
          ) : (
            <Text type="secondary">No tags</Text>
          )}
        </Space>
      ),
      width: '25%',
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: createdAt => dayjs(createdAt).format('YYYY-MM-DD HH:mm'),
      width: '15%',
      sorter: (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    },
    {
      title: 'Updated',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: updatedAt => dayjs(updatedAt).format('YYYY-MM-DD HH:mm'),
      width: '15%',
      sorter: (a, b) => new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          onClick={() => navigate(`/registry/models/${record.id}`)}
        >
          View Details
        </Button>
      ),
      width: '15%',
    },
  ]

  if (isLoading && !data) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={2} style={{ margin: 0 }}>
            <DatabaseOutlined /> Model Registry
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            Register New Model
          </Button>
        </div>
        <Text type="secondary">
          Manage model versions and deployment stages
        </Text>
      </div>

      {/* Summary Statistics */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Models"
                value={summary.totalModels}
                prefix={<DatabaseOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Versions"
                value={summary.totalVersions}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="In Production"
                value={summary.byStage?.production || 0}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="In Staging"
                value={summary.byStage?.staging || 0}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Search */}
      <Card style={{ marginBottom: 16 }}>
        <Search
          placeholder="Search models..."
          allowClear
          enterButton={<SearchOutlined />}
          size="large"
          onSearch={handleSearch}
          style={{ maxWidth: 500 }}
        />
      </Card>

      {/* Models Table */}
      <Card>
        {data?.items && data.items.length > 0 ? (
          <Table
            columns={columns}
            dataSource={data.items}
            rowKey="id"
            loading={isLoading}
            pagination={{
              current: page,
              pageSize: pageSize,
              total: data.total,
              showSizeChanger: true,
              showTotal: total => `Total ${total} models`,
              onChange: (newPage, newPageSize) => {
                setPage(newPage)
                setPageSize(newPageSize)
              },
            }}
          />
        ) : (
          <Empty
            description={
              <div>
                <p>No models registered yet</p>
                <Text type="secondary">
                  Register your first model to start versioning and deployment tracking
                </Text>
              </div>
            }
          >
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateModalOpen(true)}
            >
              Register First Model
            </Button>
          </Empty>
        )}
      </Card>

      {/* Create Model Modal */}
      <Modal
        title="Register New Model"
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
          onFinish={handleCreateModel}
        >
          <Form.Item
            name="name"
            label="Model Name"
            rules={[{ required: true, message: 'Please enter model name' }]}
          >
            <Input placeholder="e.g., credit-risk-model" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <Input.TextArea
              placeholder="Describe the purpose and use case of this model"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="Tags (comma-separated)"
          >
            <Input placeholder="e.g., classification, sklearn, production" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ModelRegistryPage
