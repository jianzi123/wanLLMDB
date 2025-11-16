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
  InputNumber,
  Card,
  message,
  Popconfirm,
} from 'antd'
import {
  ExperimentOutlined,
  PlusOutlined,
  SearchOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import type { Sweep, SweepMethod, SweepState, MetricGoal } from '@/types'
import {
  useListSweepsQuery,
  useCreateSweepMutation,
  useDeleteSweepMutation,
  useStartSweepMutation,
  usePauseSweepMutation,
  useResumeSweepMutation,
} from '@/services/sweepsApi'
import { useListProjectsQuery } from '@/services/projectsApi'

dayjs.extend(relativeTime)

const { Title } = Typography

const sweepStateConfig = {
  pending: { color: 'default', icon: <ExperimentOutlined /> },
  running: { color: 'blue', icon: <PlayCircleOutlined /> },
  paused: { color: 'orange', icon: <PauseCircleOutlined /> },
  finished: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <CloseCircleOutlined /> },
  canceled: { color: 'gray', icon: <CloseCircleOutlined /> },
}

const sweepMethodConfig = {
  random: { label: 'Random Search', color: 'blue' },
  grid: { label: 'Grid Search', color: 'purple' },
  bayes: { label: 'Bayesian (TPE)', color: 'green' },
}

function SweepsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [stateFilter, setStateFilter] = useState<SweepState | undefined>()
  const [projectFilter, setProjectFilter] = useState<string | undefined>(
    searchParams.get('project') || undefined
  )
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [form] = Form.useForm()

  const { data, isLoading } = useListSweepsQuery({
    page,
    pageSize,
    state: stateFilter,
    projectId: projectFilter,
  })

  const { data: projectsData } = useListProjectsQuery({ pageSize: 100 })
  const [createSweep, { isLoading: isCreating }] = useCreateSweepMutation()
  const [deleteSweep] = useDeleteSweepMutation()
  const [startSweep] = useStartSweepMutation()
  const [pauseSweep] = usePauseSweepMutation()
  const [resumeSweep] = useResumeSweepMutation()

  const columns: ColumnsType<Sweep> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/sweeps/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: 'Method',
      dataIndex: 'method',
      key: 'method',
      width: 150,
      render: (method: SweepMethod) => {
        const config = sweepMethodConfig[method]
        return <Tag color={config.color}>{config.label}</Tag>
      },
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      width: 120,
      render: (state: SweepState) => {
        const config = sweepStateConfig[state]
        return (
          <Tag color={config.color} icon={config.icon}>
            {state.toUpperCase()}
          </Tag>
        )
      },
    },
    {
      title: 'Metric',
      key: 'metric',
      width: 180,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <strong>{record.metricName}</strong>
          <Tag color={record.metricGoal === 'maximize' ? 'green' : 'blue'} style={{ fontSize: 11 }}>
            {record.metricGoal}
          </Tag>
        </Space>
      ),
    },
    {
      title: 'Runs',
      key: 'runs',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <strong>{record.runCount}</strong>
          {record.runCap && (
            <span style={{ fontSize: 11, color: '#999' }}>/ {record.runCap}</span>
          )}
        </Space>
      ),
    },
    {
      title: 'Best Value',
      dataIndex: 'bestValue',
      key: 'bestValue',
      width: 120,
      render: (value) => (value !== null && value !== undefined ? value.toFixed(4) : '-'),
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
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/sweeps/${record.id}`)}
          >
            View
          </Button>
          {record.state === 'pending' && (
            <Button
              type="link"
              size="small"
              onClick={async () => {
                try {
                  await startSweep(record.id).unwrap()
                  message.success('Sweep started')
                } catch (error) {
                  message.error('Failed to start sweep')
                }
              }}
            >
              Start
            </Button>
          )}
          {record.state === 'running' && (
            <Button
              type="link"
              size="small"
              onClick={async () => {
                try {
                  await pauseSweep(record.id).unwrap()
                  message.success('Sweep paused')
                } catch (error) {
                  message.error('Failed to pause sweep')
                }
              }}
            >
              Pause
            </Button>
          )}
          {record.state === 'paused' && (
            <Button
              type="link"
              size="small"
              onClick={async () => {
                try {
                  await resumeSweep(record.id).unwrap()
                  message.success('Sweep resumed')
                } catch (error) {
                  message.error('Failed to resume sweep')
                }
              }}
            >
              Resume
            </Button>
          )}
          <Popconfirm
            title="Delete sweep"
            description="Are you sure? This will also delete all associated runs."
            onConfirm={async () => {
              try {
                await deleteSweep(record.id).unwrap()
                message.success('Sweep deleted')
              } catch (error) {
                message.error('Failed to delete sweep')
              }
            }}
          >
            <Button type="link" danger size="small">
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleCreate = async (values: any) => {
    try {
      const sweep = await createSweep({
        name: values.name,
        description: values.description,
        projectId: values.projectId,
        method: values.method,
        metricName: values.metricName,
        metricGoal: values.metricGoal,
        config: values.config || {},
        runCap: values.runCap,
      }).unwrap()
      message.success('Sweep created successfully')
      setIsCreateModalOpen(false)
      form.resetFields()
      navigate(`/sweeps/${sweep.id}`)
    } catch (error) {
      message.error('Failed to create sweep')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>Hyperparameter Sweeps</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsCreateModalOpen(true)}
        >
          New Sweep
        </Button>
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="Filter by state"
          allowClear
          style={{ width: 150 }}
          onChange={setStateFilter}
          options={Object.entries(sweepStateConfig).map(([value, config]) => ({
            value,
            label: (
              <span>
                {config.icon} {value.toUpperCase()}
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
          showTotal: (total) => `Total ${total} sweeps`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize)
          },
        }}
      />

      <Modal
        title="Create New Sweep"
        open={isCreateModalOpen}
        onCancel={() => {
          setIsCreateModalOpen(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        confirmLoading={isCreating}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter sweep name' }]}
          >
            <Input placeholder="my-hyperparameter-search" />
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
            label="Method"
            name="method"
            rules={[{ required: true, message: 'Please select optimization method' }]}
            initialValue="random"
          >
            <Select>
              <Select.Option value="random">Random Search</Select.Option>
              <Select.Option value="grid">Grid Search</Select.Option>
              <Select.Option value="bayes">Bayesian Optimization (TPE)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Metric Name"
            name="metricName"
            rules={[{ required: true, message: 'Please enter metric name' }]}
          >
            <Input placeholder="accuracy" />
          </Form.Item>

          <Form.Item
            label="Metric Goal"
            name="metricGoal"
            rules={[{ required: true, message: 'Please select metric goal' }]}
            initialValue="maximize"
          >
            <Select>
              <Select.Option value="maximize">Maximize</Select.Option>
              <Select.Option value="minimize">Minimize</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Run Cap (Optional)"
            name="runCap"
          >
            <InputNumber min={1} style={{ width: '100%' }} placeholder="Maximum number of runs" />
          </Form.Item>

          <Form.Item
            label="Description"
            name="description"
          >
            <Input.TextArea
              rows={3}
              placeholder="Describe your hyperparameter search..."
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SweepsPage
