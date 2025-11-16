import { useState, useEffect } from 'react'
import { Card, Row, Col, Select, Space, Button, Tag, Empty, message } from 'antd'
import { ReloadOutlined, FullscreenOutlined } from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import MetricLineChart from '@/components/charts/MetricLineChart'
import { useGetRunQuery } from '@/services/runsApi'
import { useGetRunMetricsQuery } from '@/services/metricsApi'
import type { Metric } from '@/types'

const { Option } = Select

function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null)

  const { data: run, isLoading: runLoading } = useGetRunQuery(id!, { skip: !id })
  const { data: metricsData, isLoading: metricsLoading, refetch } = useGetRunMetricsQuery(
    { runId: id!, params: { limit: 10000 } },
    { skip: !id, pollingInterval: autoRefresh ? 5000 : 0 }
  )

  useEffect(() => {
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    }
  }, [refreshInterval])

  const handleRefresh = async () => {
    try {
      await refetch()
      message.success('Metrics refreshed')
    } catch (error) {
      message.error('Failed to refresh metrics')
    }
  }

  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh)
    message.info(autoRefresh ? 'Auto-refresh disabled' : 'Auto-refresh enabled (5s interval)')
  }

  // Get available metric names
  const availableMetrics = Array.from(
    new Set(metricsData?.metrics?.map((m: Metric) => m.metric_name) || [])
  )

  // Filter metrics based on selection
  const filteredMetrics = selectedMetrics.length > 0
    ? metricsData?.metrics?.filter((m: Metric) => selectedMetrics.includes(m.metric_name)) || []
    : metricsData?.metrics || []

  if (runLoading) {
    return <Card loading />
  }

  if (!run) {
    return (
      <Card>
        <Empty description="Run not found" />
      </Card>
    )
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <h2 style={{ margin: 0 }}>{run.name}</h2>
              <Space>
                <Tag color={run.state === 'running' ? 'blue' : run.state === 'finished' ? 'green' : 'red'}>
                  {run.state.toUpperCase()}
                </Tag>
                {run.git_branch && <Tag>{run.git_branch}</Tag>}
                {run.tags?.map((tag) => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Space>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                mode="multiple"
                placeholder="Select metrics to display"
                style={{ minWidth: 300 }}
                value={selectedMetrics}
                onChange={setSelectedMetrics}
                maxTagCount="responsive"
              >
                {availableMetrics.map((metric) => (
                  <Option key={metric} value={metric}>
                    {metric}
                  </Option>
                ))}
              </Select>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={metricsLoading}>
                Refresh
              </Button>
              <Button
                type={autoRefresh ? 'primary' : 'default'}
                onClick={toggleAutoRefresh}
              >
                {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Metrics Grid */}
      {availableMetrics.length === 0 ? (
        <Card>
          <Empty
            description={
              <Space direction="vertical">
                <span>No metrics data available yet</span>
                <span style={{ fontSize: 12, color: '#999' }}>
                  Metrics will appear here when your training script logs them
                </span>
              </Space>
            }
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {/* Main chart - all selected metrics */}
          <Col span={24}>
            <MetricLineChart
              title="Metrics Over Time"
              metrics={filteredMetrics}
              loading={metricsLoading}
              height={400}
              xAxisKey="step"
            />
          </Col>

          {/* Individual metric charts */}
          {selectedMetrics.length > 0 &&
            selectedMetrics.map((metricName) => (
              <Col xs={24} lg={12} key={metricName}>
                <MetricLineChart
                  title={metricName}
                  metrics={filteredMetrics.filter((m: Metric) => m.metric_name === metricName)}
                  loading={metricsLoading}
                  height={300}
                  showLegend={false}
                  yAxisLabel={metricName}
                  xAxisKey="step"
                />
              </Col>
            ))}

          {/* Time-based view */}
          {selectedMetrics.length > 0 && (
            <Col span={24}>
              <MetricLineChart
                title="Metrics Over Time (Time-based)"
                metrics={filteredMetrics}
                loading={metricsLoading}
                height={400}
                xAxisKey="time"
              />
            </Col>
          )}
        </Row>
      )}
    </div>
  )
}

export default WorkspacePage
