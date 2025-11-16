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
  message,
  Statistic,
  Row,
  Col,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import type { SweepRunDetail, SweepMethod, SweepState } from '@/types'
import {
  useGetSweepQuery,
  useListSweepRunsQuery,
  useGetParallelCoordinatesDataQuery,
  useStartSweepMutation,
  usePauseSweepMutation,
  useResumeSweepMutation,
  useFinishSweepMutation,
} from '@/services/sweepsApi'
import ParallelCoordinatesChart from '@/components/charts/ParallelCoordinatesChart'

const { Title, Text } = Typography

const sweepStateConfig = {
  pending: { color: 'default', icon: <PlayCircleOutlined /> },
  running: { color: 'blue', icon: <PlayCircleOutlined /> },
  paused: { color: 'orange', icon: <PauseCircleOutlined /> },
  finished: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <StopOutlined /> },
  canceled: { color: 'gray', icon: <StopOutlined /> },
}

const sweepMethodConfig = {
  random: { label: 'Random Search', color: 'blue' },
  grid: { label: 'Grid Search', color: 'purple' },
  bayes: { label: 'Bayesian (TPE)', color: 'green' },
}

function SweepDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: sweep, isLoading } = useGetSweepQuery(id!)
  const { data: sweepRunsData } = useListSweepRunsQuery({ sweepId: id! }, { skip: !id })
  const { data: parallelData } = useGetParallelCoordinatesDataQuery(id!, { skip: !id })

  const [startSweep] = useStartSweepMutation()
  const [pauseSweep] = usePauseSweepMutation()
  const [resumeSweep] = useResumeSweepMutation()
  const [finishSweep] = useFinishSweepMutation()

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!sweep) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="Sweep not found" />
      </div>
    )
  }

  const config = sweepStateConfig[sweep.state]
  const methodConfig = sweepMethodConfig[sweep.method]

  const handleStart = async () => {
    try {
      await startSweep(id!).unwrap()
      message.success('Sweep started')
    } catch (error) {
      message.error('Failed to start sweep')
    }
  }

  const handlePause = async () => {
    try {
      await pauseSweep(id!).unwrap()
      message.success('Sweep paused')
    } catch (error) {
      message.error('Failed to pause sweep')
    }
  }

  const handleResume = async () => {
    try {
      await resumeSweep(id!).unwrap()
      message.success('Sweep resumed')
    } catch (error) {
      message.error('Failed to resume sweep')
    }
  }

  const handleFinish = async () => {
    try {
      await finishSweep(id!).unwrap()
      message.success('Sweep finished')
    } catch (error) {
      message.error('Failed to finish sweep')
    }
  }

  const runColumns: ColumnsType<SweepRunDetail> = [
    {
      title: 'Trial #',
      dataIndex: 'trialNumber',
      key: 'trialNumber',
      width: 80,
      render: (num) => num ?? '-',
    },
    {
      title: 'Run',
      key: 'run',
      render: (_, record) => (
        <a onClick={() => navigate(`/runs/${record.runId}`)}>
          {record.run?.name || record.runId.substring(0, 8)}
        </a>
      ),
    },
    {
      title: 'Parameters',
      dataIndex: 'suggestedParams',
      key: 'suggestedParams',
      render: (params) => {
        if (!params) return '-'
        return (
          <Space wrap size={4}>
            {Object.entries(params).map(([key, value]) => (
              <Tag key={key}>
                {key}: {typeof value === 'number' ? value.toFixed(4) : String(value)}
              </Tag>
            ))}
          </Space>
        )
      },
    },
    {
      title: 'Metric Value',
      dataIndex: 'metricValue',
      key: 'metricValue',
      width: 120,
      render: (value) => (value !== null && value !== undefined ? value.toFixed(4) : '-'),
    },
    {
      title: 'Best',
      dataIndex: 'isBest',
      key: 'isBest',
      width: 80,
      render: (isBest) =>
        isBest ? <Tag color="gold">Best</Tag> : null,
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
  ]

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate(-1)}
          style={{ marginBottom: 16 }}
        >
          Back
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
              {sweep.name}
            </Title>
            <Space size={8}>
              <Tag color={config.color} icon={config.icon}>
                {sweep.state.toUpperCase()}
              </Tag>
              <Tag color={methodConfig.color}>{methodConfig.label}</Tag>
            </Space>
          </div>
          <Space>
            {sweep.state === 'pending' && (
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleStart}>
                Start Sweep
              </Button>
            )}
            {sweep.state === 'running' && (
              <>
                <Button icon={<PauseCircleOutlined />} onClick={handlePause}>
                  Pause
                </Button>
                <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleFinish}>
                  Finish
                </Button>
              </>
            )}
            {sweep.state === 'paused' && (
              <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleResume}>
                Resume
              </Button>
            )}
          </Space>
        </div>
      </div>

      {/* Statistics */}
      {sweep.stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Runs"
                value={sweep.stats.totalRuns}
                suffix={sweep.runCap ? `/ ${sweep.runCap}` : ''}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Completed"
                value={sweep.stats.completedRuns}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Running"
                value={sweep.stats.runningRuns}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Best Value"
                value={sweep.stats.bestValue?.toFixed(4) || '-'}
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Tabs */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Overview" key="overview">
          <Card>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="ID">{sweep.id}</Descriptions.Item>
              <Descriptions.Item label="Method">
                <Tag color={methodConfig.color}>{methodConfig.label}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Metric Name">
                {sweep.metricName}
              </Descriptions.Item>
              <Descriptions.Item label="Metric Goal">
                <Tag color={sweep.metricGoal === 'maximize' ? 'green' : 'blue'}>
                  {sweep.metricGoal.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Run Count">
                {sweep.runCount}
              </Descriptions.Item>
              <Descriptions.Item label="Run Cap">
                {sweep.runCap || 'Unlimited'}
              </Descriptions.Item>
              <Descriptions.Item label="Best Run ID">
                {sweep.bestRunId ? (
                  <a onClick={() => navigate(`/runs/${sweep.bestRunId}`)}>
                    {sweep.bestRunId.substring(0, 8)}
                  </a>
                ) : (
                  '-'
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Best Value">
                {sweep.bestValue !== null && sweep.bestValue !== undefined
                  ? sweep.bestValue.toFixed(4)
                  : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {dayjs(sweep.createdAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Updated">
                {dayjs(sweep.updatedAt).fromNow()}
              </Descriptions.Item>
              {sweep.description && (
                <Descriptions.Item label="Description" span={2}>
                  {sweep.description}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="Hyperparameter Space" span={2}>
                <pre style={{ margin: 0, fontSize: 12 }}>
                  {JSON.stringify(sweep.config, null, 2)}
                </pre>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={`Runs (${sweep.runCount})`} key="runs">
          <Card>
            <Table
              columns={runColumns}
              dataSource={sweepRunsData?.items || []}
              rowKey="id"
              pagination={false}
            />
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab="Best Parameters" key="best">
          <Card>
            {sweep.stats?.bestParams ? (
              <Descriptions column={1} bordered>
                {Object.entries(sweep.stats.bestParams).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key}>
                    {typeof value === 'number' ? value.toFixed(6) : String(value)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            ) : (
              <Empty description="No best parameters yet" />
            )}
          </Card>
        </Tabs.TabPane>

        {sweep.stats?.parameterImportance && (
          <Tabs.TabPane tab="Parameter Importance" key="importance">
            <Card>
              <Table
                dataSource={Object.entries(sweep.stats.parameterImportance).map(([param, importance]) => ({
                  param,
                  importance,
                }))}
                columns={[
                  {
                    title: 'Parameter',
                    dataIndex: 'param',
                    key: 'param',
                  },
                  {
                    title: 'Importance',
                    dataIndex: 'importance',
                    key: 'importance',
                    render: (value) => (
                      <div style={{ width: '100%' }}>
                        <div>{value.toFixed(4)}</div>
                        <div
                          style={{
                            width: `${value * 100}%`,
                            height: 4,
                            background: '#1890ff',
                            marginTop: 4,
                          }}
                        />
                      </div>
                    ),
                  },
                ]}
                pagination={false}
              />
            </Card>
          </Tabs.TabPane>
        )}

        <Tabs.TabPane tab="Visualization" key="visualization">
          {parallelData && parallelData.data.length > 0 ? (
            <ParallelCoordinatesChart data={parallelData} />
          ) : (
            <Card>
              <Empty description="No data available for visualization. Complete some runs first." />
            </Card>
          )}
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default SweepDetailPage
