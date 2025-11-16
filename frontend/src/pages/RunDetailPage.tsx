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
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  TagsOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import { useGetRunQuery, useFinishRunMutation } from '@/services/runsApi'
import RunFilesTab from '@/components/RunFilesTab'
import LogViewer from '@/components/LogViewer'

dayjs.extend(duration)

const { Title, Text } = Typography

const stateConfig = {
  running: { color: 'blue', icon: <PlayCircleOutlined /> },
  finished: { color: 'green', icon: <CheckCircleOutlined /> },
  crashed: { color: 'red', icon: <CloseCircleOutlined /> },
  killed: { color: 'orange', icon: <StopOutlined /> },
}

function RunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: run, isLoading } = useGetRunQuery(id!)
  const [finishRun] = useFinishRunMutation()

  const handleFinish = async () => {
    if (!id) return
    try {
      await finishRun({ id, exitCode: 0 }).unwrap()
      message.success('Run finished successfully!')
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to finish run')
    }
  }

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!run) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="Run not found" />
      </div>
    )
  }

  const config = stateConfig[run.state as keyof typeof stateConfig]
  const runDuration = run.finishedAt
    ? dayjs(run.finishedAt).diff(dayjs(run.startedAt), 'second')
    : dayjs().diff(dayjs(run.startedAt), 'second')

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
              {run.name || `Run ${run.id.substring(0, 8)}`}
            </Title>
            <Space size={8}>
              <Tag color={config.color} icon={config.icon}>
                {run.state.toUpperCase()}
              </Tag>
              {run.tags?.map(tag => (
                <Tag key={tag} icon={<TagsOutlined />}>
                  {tag}
                </Tag>
              ))}
            </Space>
          </div>
          {run.state === 'running' && (
            <Button type="primary" onClick={handleFinish}>
              Finish Run
            </Button>
          )}
        </div>
      </div>

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
                <Descriptions title="Run Information" column={2} bordered>
                  <Descriptions.Item label="Run ID" span={2}>
                    <Text code copyable>
                      {run.id}
                    </Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="State">
                    <Tag color={config.color} icon={config.icon}>
                      {run.state.toUpperCase()}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Duration">
                    {dayjs.duration(runDuration, 'seconds').format('HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Started At">
                    {dayjs(run.startedAt).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Finished At">
                    {run.finishedAt
                      ? dayjs(run.finishedAt).format('YYYY-MM-DD HH:mm:ss')
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tags" span={2}>
                    {run.tags?.length > 0 ? (
                      <Space size={4} wrap>
                        {run.tags.map(tag => (
                          <Tag key={tag}>{tag}</Tag>
                        ))}
                      </Space>
                    ) : (
                      <Text type="secondary">No tags</Text>
                    )}
                  </Descriptions.Item>
                </Descriptions>

                {/* Git Information */}
                {(run.gitCommit || run.gitBranch || run.gitRemote) && (
                  <Descriptions
                    title="Git Information"
                    column={2}
                    bordered
                    style={{ marginTop: 24 }}
                  >
                    {run.gitBranch && (
                      <Descriptions.Item label="Branch">
                        <Tag>{run.gitBranch}</Tag>
                      </Descriptions.Item>
                    )}
                    {run.gitCommit && (
                      <Descriptions.Item label="Commit">
                        <Text code copyable>
                          {run.gitCommit.substring(0, 8)}
                        </Text>
                      </Descriptions.Item>
                    )}
                    {run.gitRemote && (
                      <Descriptions.Item label="Remote" span={2}>
                        <Text code>{run.gitRemote}</Text>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                )}

                {/* Environment Information */}
                {(run.host || run.os || run.pythonVersion) && (
                  <Descriptions
                    title="Environment"
                    column={2}
                    bordered
                    style={{ marginTop: 24 }}
                  >
                    {run.host && (
                      <Descriptions.Item label="Host">{run.host}</Descriptions.Item>
                    )}
                    {run.os && (
                      <Descriptions.Item label="OS">{run.os}</Descriptions.Item>
                    )}
                    {run.pythonVersion && (
                      <Descriptions.Item label="Python Version" span={2}>
                        {run.pythonVersion}
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                )}

                {/* Notes */}
                {run.notes && (
                  <Card title="Notes" style={{ marginTop: 24 }}>
                    <Text>{run.notes}</Text>
                  </Card>
                )}
              </Card>
            ),
          },
          {
            key: 'metrics',
            label: 'Metrics',
            children: (
              <Card>
                <Empty description="Metrics visualization will be implemented in Sprint 3" />
              </Card>
            ),
          },
          {
            key: 'config',
            label: 'Config',
            children: (
              <Card>
                {run.config && Object.keys(run.config).length > 0 ? (
                  <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
                    {JSON.stringify(run.config, null, 2)}
                  </pre>
                ) : (
                  <Empty description="No configuration data" />
                )}
              </Card>
            ),
          },
          {
            key: 'files',
            label: 'Files',
            children: <RunFilesTab runId={id!} />,
          },
          {
            key: 'logs',
            label: 'Logs',
            children: <LogViewer runId={id!} />,
          },
        ]}
      />
    </div>
  )
}

export default RunDetailPage
