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
  Modal,
  Form,
  Input,
  Select,
  message,
  Timeline,
  Row,
  Col,
  Statistic,
  Alert,
} from 'antd'
import {
  ArrowLeftOutlined,
  DatabaseOutlined,
  PlusOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  HistoryOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import {
  useGetModelQuery,
  useListVersionsQuery,
  useCreateVersionMutation,
  useTransitionStageMutation,
  useGetTransitionHistoryQuery,
  ModelStage,
  type ModelVersion,
  type ModelVersionTransition,
} from '@/services/modelRegistryApi'

dayjs.extend(relativeTime)

const { Title, Text, Paragraph } = Typography

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

// Helper function to get stage icon
const getStageIcon = (stage: ModelStage) => {
  switch (stage) {
    case ModelStage.PRODUCTION:
      return <RocketOutlined />
    case ModelStage.STAGING:
      return <ExperimentOutlined />
    case ModelStage.ARCHIVED:
      return <InboxOutlined />
    default:
      return <DatabaseOutlined />
  }
}

function ModelDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedVersionId, setSelectedVersionId] = useState<string>()
  const [isCreateVersionModalOpen, setIsCreateVersionModalOpen] = useState(false)
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false)
  const [versionForm] = Form.useForm()
  const [transitionForm] = Form.useForm()

  const { data: model, isLoading } = useGetModelQuery(id!)
  const { data: versionsData } = useListVersionsQuery(
    { modelId: id!, skip: 0, limit: 100 },
    { skip: !id }
  )
  const { data: transitionsData } = useGetTransitionHistoryQuery(selectedVersionId!, {
    skip: !selectedVersionId,
  })

  const [createVersion, { isLoading: isCreatingVersion }] = useCreateVersionMutation()
  const [transitionStage, { isLoading: isTransitioning }] = useTransitionStageMutation()

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!model) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="Model not found" />
      </div>
    )
  }

  const handleCreateVersion = async (values: any) => {
    try {
      await createVersion({
        modelId: id!,
        data: {
          version: values.version,
          description: values.description,
          runId: values.runId || undefined,
          artifactVersionId: values.artifactVersionId || undefined,
          metrics: values.metrics ? JSON.parse(values.metrics) : {},
          tags: values.tags ? values.tags.split(',').map((t: string) => t.trim()) : [],
          metadata: values.metadata ? JSON.parse(values.metadata) : {},
        },
      }).unwrap()

      message.success('Model version created successfully')
      setIsCreateVersionModalOpen(false)
      versionForm.resetFields()
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to create version')
    }
  }

  const handleTransitionStage = async (values: any) => {
    if (!selectedVersionId) return

    try {
      await transitionStage({
        versionId: selectedVersionId,
        data: {
          stage: values.stage,
          comment: values.comment,
        },
      }).unwrap()

      message.success('Stage transition successful')
      setIsTransitionModalOpen(false)
      transitionForm.resetFields()
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to transition stage')
    }
  }

  const selectedVersion = versionsData?.items?.find((v) => v.id === selectedVersionId)

  const versionColumns: ColumnsType<ModelVersion> = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      render: (text, record) => (
        <Button
          type="link"
          onClick={() => setSelectedVersionId(record.id)}
          style={{ padding: 0 }}
        >
          <Text strong>{text}</Text>
        </Button>
      ),
      width: '15%',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <Text type="secondary">No description</Text>,
      width: '25%',
    },
    {
      title: 'Stage',
      dataIndex: 'stage',
      key: 'stage',
      render: (stage: ModelStage) => (
        <Tag color={getStageColor(stage)} icon={getStageIcon(stage)}>
          {stage.toUpperCase()}
        </Tag>
      ),
      width: '15%',
    },
    {
      title: 'Metrics',
      dataIndex: 'metrics',
      key: 'metrics',
      render: (metrics: Record<string, any>) => {
        if (!metrics || Object.keys(metrics).length === 0) {
          return <Text type="secondary">No metrics</Text>
        }
        const keys = Object.keys(metrics).slice(0, 3)
        return (
          <Space size={4} wrap>
            {keys.map((key) => (
              <Tag key={key}>
                {key}: {typeof metrics[key] === 'number' ? metrics[key].toFixed(4) : metrics[key]}
              </Tag>
            ))}
            {Object.keys(metrics).length > 3 && <Tag>+{Object.keys(metrics).length - 3}</Tag>}
          </Space>
        )
      },
      width: '20%',
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
      width: '15%',
      sorter: (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          onClick={() => {
            setSelectedVersionId(record.id)
            setIsTransitionModalOpen(true)
          }}
        >
          Transition Stage
        </Button>
      ),
      width: '10%',
    },
  ]

  const stageStats = versionsData?.items?.reduce(
    (acc, version) => {
      acc[version.stage] = (acc[version.stage] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/registry/models')}
          style={{ marginBottom: 16 }}
        >
          Back to Models
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
              <DatabaseOutlined /> {model.name}
            </Title>
            {model.description && (
              <Paragraph type="secondary" style={{ marginBottom: 8 }}>
                {model.description}
              </Paragraph>
            )}
            <Space size={4} wrap>
              {model.tags?.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsCreateVersionModalOpen(true)}
            >
              Create Version
            </Button>
          </Space>
        </div>
      </div>

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Versions"
              value={versionsData?.total || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Production"
              value={stageStats?.[ModelStage.PRODUCTION] || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Staging"
              value={stageStats?.[ModelStage.STAGING] || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Archived"
              value={stageStats?.[ModelStage.ARCHIVED] || 0}
              valueStyle={{ color: '#999' }}
              prefix={<InboxOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Overview" key="overview">
          <Card>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="Model ID">{model.id}</Descriptions.Item>
              <Descriptions.Item label="Project ID">{model.projectId}</Descriptions.Item>
              <Descriptions.Item label="Created By">{model.createdBy}</Descriptions.Item>
              <Descriptions.Item label="Created At">
                {dayjs(model.createdAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Updated At">
                {dayjs(model.updatedAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Total Versions">
                {versionsData?.total || 0}
              </Descriptions.Item>
              {model.description && (
                <Descriptions.Item label="Description" span={2}>
                  {model.description}
                </Descriptions.Item>
              )}
              {model.tags && model.tags.length > 0 && (
                <Descriptions.Item label="Tags" span={2}>
                  <Space wrap>
                    {model.tags.map((tag) => (
                      <Tag key={tag}>{tag}</Tag>
                    ))}
                  </Space>
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={`Versions (${versionsData?.total || 0})`} key="versions">
          <Card>
            {versionsData?.items && versionsData.items.length > 0 ? (
              <Table
                columns={versionColumns}
                dataSource={versionsData.items}
                rowKey="id"
                pagination={false}
              />
            ) : (
              <Empty
                description="No versions yet"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setIsCreateVersionModalOpen(true)}
                >
                  Create First Version
                </Button>
              </Empty>
            )}

            {/* Selected Version Details */}
            {selectedVersion && (
              <Card
                title={`Version ${selectedVersion.version} Details`}
                style={{ marginTop: 16 }}
                extra={
                  <Tag color={getStageColor(selectedVersion.stage)} icon={getStageIcon(selectedVersion.stage)}>
                    {selectedVersion.stage.toUpperCase()}
                  </Tag>
                }
              >
                <Descriptions column={2} bordered>
                  <Descriptions.Item label="Version ID">{selectedVersion.id}</Descriptions.Item>
                  <Descriptions.Item label="Version">{selectedVersion.version}</Descriptions.Item>
                  <Descriptions.Item label="Stage">
                    <Tag color={getStageColor(selectedVersion.stage)} icon={getStageIcon(selectedVersion.stage)}>
                      {selectedVersion.stage.toUpperCase()}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Created">
                    {dayjs(selectedVersion.createdAt).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  {selectedVersion.runId && (
                    <Descriptions.Item label="Run ID">
                      <Button
                        type="link"
                        icon={<LinkOutlined />}
                        onClick={() => navigate(`/runs/${selectedVersion.runId}`)}
                        style={{ padding: 0 }}
                      >
                        {selectedVersion.runId}
                      </Button>
                    </Descriptions.Item>
                  )}
                  {selectedVersion.artifactVersionId && (
                    <Descriptions.Item label="Artifact Version">
                      {selectedVersion.artifactVersionId}
                    </Descriptions.Item>
                  )}
                  {selectedVersion.approvedBy && (
                    <>
                      <Descriptions.Item label="Approved By">
                        {selectedVersion.approvedBy}
                      </Descriptions.Item>
                      <Descriptions.Item label="Approved At">
                        {dayjs(selectedVersion.approvedAt).format('YYYY-MM-DD HH:mm:ss')}
                      </Descriptions.Item>
                    </>
                  )}
                  {selectedVersion.description && (
                    <Descriptions.Item label="Description" span={2}>
                      {selectedVersion.description}
                    </Descriptions.Item>
                  )}
                  {selectedVersion.tags && selectedVersion.tags.length > 0 && (
                    <Descriptions.Item label="Tags" span={2}>
                      <Space wrap>
                        {selectedVersion.tags.map((tag: string) => (
                          <Tag key={tag}>{tag}</Tag>
                        ))}
                      </Space>
                    </Descriptions.Item>
                  )}
                  {selectedVersion.metrics && Object.keys(selectedVersion.metrics).length > 0 && (
                    <Descriptions.Item label="Metrics" span={2}>
                      <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                        {JSON.stringify(selectedVersion.metrics, null, 2)}
                      </pre>
                    </Descriptions.Item>
                  )}
                  {selectedVersion.metadata && Object.keys(selectedVersion.metadata).length > 0 && (
                    <Descriptions.Item label="Metadata" span={2}>
                      <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                        {JSON.stringify(selectedVersion.metadata, null, 2)}
                      </pre>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            )}
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane
          tab={
            <span>
              <HistoryOutlined /> Transition History
            </span>
          }
          key="history"
          disabled={!selectedVersionId}
        >
          <Card>
            {!selectedVersionId ? (
              <Alert
                message="Select a version to view its transition history"
                type="info"
                showIcon
              />
            ) : transitionsData && transitionsData.items.length > 0 ? (
              <Timeline>
                {transitionsData.items.map((transition: ModelVersionTransition) => (
                  <Timeline.Item
                    key={transition.id}
                    dot={<CheckCircleOutlined />}
                    color={getStageColor(transition.toStage)}
                  >
                    <Space direction="vertical" size={4}>
                      <Space>
                        <Text strong>
                          {transition.fromStage.toUpperCase()} → {transition.toStage.toUpperCase()}
                        </Text>
                        <Tag color={getStageColor(transition.toStage)}>
                          {transition.toStage.toUpperCase()}
                        </Tag>
                      </Space>
                      <Text type="secondary">
                        {dayjs(transition.transitionedAt).format('YYYY-MM-DD HH:mm:ss')} by{' '}
                        {transition.transitionedBy}
                      </Text>
                      {transition.comment && (
                        <Paragraph style={{ marginBottom: 0 }}>
                          <Text italic>"{transition.comment}"</Text>
                        </Paragraph>
                      )}
                    </Space>
                  </Timeline.Item>
                ))}
              </Timeline>
            ) : (
              <Empty description="No transition history" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Tabs.TabPane>
      </Tabs>

      {/* Create Version Modal */}
      <Modal
        title="Create New Version"
        open={isCreateVersionModalOpen}
        onCancel={() => {
          setIsCreateVersionModalOpen(false)
          versionForm.resetFields()
        }}
        onOk={() => versionForm.submit()}
        confirmLoading={isCreatingVersion}
        width={600}
      >
        <Form form={versionForm} layout="vertical" onFinish={handleCreateVersion}>
          <Form.Item
            name="version"
            label="Version"
            rules={[{ required: true, message: 'Please enter version' }]}
          >
            <Input placeholder="e.g., v1.0.0, 2024.01.15" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Describe this version..." />
          </Form.Item>

          <Form.Item name="runId" label="Run ID (optional)">
            <Input placeholder="UUID of the training run" />
          </Form.Item>

          <Form.Item name="artifactVersionId" label="Artifact Version ID (optional)">
            <Input placeholder="UUID of the model artifact version" />
          </Form.Item>

          <Form.Item name="metrics" label="Metrics (JSON)">
            <Input.TextArea
              rows={4}
              placeholder='{"accuracy": 0.95, "f1_score": 0.92}'
            />
          </Form.Item>

          <Form.Item name="tags" label="Tags (comma-separated)">
            <Input placeholder="e.g., production-ready, validated, pytorch" />
          </Form.Item>

          <Form.Item name="metadata" label="Metadata (JSON)">
            <Input.TextArea
              rows={3}
              placeholder='{"framework": "pytorch", "python_version": "3.9"}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Transition Stage Modal */}
      <Modal
        title={`Transition Version ${selectedVersion?.version}`}
        open={isTransitionModalOpen}
        onCancel={() => {
          setIsTransitionModalOpen(false)
          transitionForm.resetFields()
        }}
        onOk={() => transitionForm.submit()}
        confirmLoading={isTransitioning}
      >
        <Form form={transitionForm} layout="vertical" onFinish={handleTransitionStage}>
          <Form.Item
            name="stage"
            label="Target Stage"
            rules={[{ required: true, message: 'Please select target stage' }]}
          >
            <Select placeholder="Select stage">
              <Select.Option value={ModelStage.NONE}>
                <Tag color={getStageColor(ModelStage.NONE)} icon={getStageIcon(ModelStage.NONE)}>
                  NONE
                </Tag>
              </Select.Option>
              <Select.Option value={ModelStage.STAGING}>
                <Tag color={getStageColor(ModelStage.STAGING)} icon={getStageIcon(ModelStage.STAGING)}>
                  STAGING
                </Tag>
              </Select.Option>
              <Select.Option value={ModelStage.PRODUCTION}>
                <Tag color={getStageColor(ModelStage.PRODUCTION)} icon={getStageIcon(ModelStage.PRODUCTION)}>
                  PRODUCTION
                </Tag>
              </Select.Option>
              <Select.Option value={ModelStage.ARCHIVED}>
                <Tag color={getStageColor(ModelStage.ARCHIVED)} icon={getStageIcon(ModelStage.ARCHIVED)}>
                  ARCHIVED
                </Tag>
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="comment" label="Comment">
            <Input.TextArea
              rows={3}
              placeholder="Add a comment about this transition..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ModelDetailPage
