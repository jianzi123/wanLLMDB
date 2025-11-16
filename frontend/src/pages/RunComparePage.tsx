import { useState, useMemo } from 'react'
import { Card, Table, Select, Space, Button, Row, Col, Statistic, Empty, Tag } from 'antd'
import { CompareOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useListRunsQuery } from '@/services/runsApi'
import { useGetRunMetricsQuery } from '@/services/metricsApi'
import MetricLineChart from '@/components/charts/MetricLineChart'
import type { Run, Metric } from '@/types'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'

dayjs.extend(duration)

const { Option } = Select

interface RunComparison {
  run: Run
  metrics?: Metric[]
}

function RunComparePage() {
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [selectedMetric, setSelectedMetric] = useState<string>()

  const { data: runsData, isLoading: runsLoading } = useListRunsQuery({
    page: 1,
    pageSize: 100,
    state: 'finished',
  })

  // Fetch metrics for selected runs
  const selectedRuns: RunComparison[] = useMemo(() => {
    if (!selectedRunIds.length || !runsData?.items) return []

    return selectedRunIds.map(runId => {
      const run = runsData.items.find(r => r.id === runId)
      return { run: run! }
    }).filter(r => r.run)
  }, [selectedRunIds, runsData])

  // Get all unique metric names from selected runs
  const availableMetrics = useMemo(() => {
    const metrics = new Set<string>()
    selectedRuns.forEach(({ run }) => {
      if (run.summary) {
        Object.keys(run.summary).forEach(key => metrics.add(key))
      }
    })
    return Array.from(metrics)
  }, [selectedRuns])

  const handleRunSelect = (value: string[]) => {
    setSelectedRunIds(value)
  }

  const handleClearSelection = () => {
    setSelectedRunIds([])
    setSelectedMetric(undefined)
  }

  // Calculate statistics for each run
  const comparisonData = selectedRuns.map(({ run }) => {
    const startedAt = dayjs(run.startedAt)
    const finishedAt = run.finishedAt ? dayjs(run.finishedAt) : dayjs()
    const durationMs = finishedAt.diff(startedAt)
    const durationStr = dayjs.duration(durationMs).format('HH:mm:ss')

    return {
      key: run.id,
      id: run.id,
      name: run.name || run.id.substring(0, 8),
      state: run.state,
      duration: durationStr,
      durationMs,
      createdAt: run.startedAt,
      config: run.config,
      summary: run.summary || {},
      tags: run.tags,
      gitBranch: run.gitBranch,
      gitCommit: run.gitCommit?.substring(0, 7),
    }
  })

  const columns: ColumnsType<any> = [
    {
      title: 'Run Name',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left',
      width: 150,
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <strong>{text}</strong>
          <span style={{ fontSize: 12, color: '#999' }}>{record.id.substring(0, 8)}</span>
        </Space>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      width: 100,
      render: (state) => {
        const config = {
          running: { color: 'blue', text: 'Running' },
          finished: { color: 'green', text: 'Finished' },
          crashed: { color: 'red', text: 'Crashed' },
          killed: { color: 'orange', text: 'Killed' },
        }[state] || { color: 'default', text: state }

        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 120,
    },
    {
      title: 'Started',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Git Branch',
      dataIndex: 'gitBranch',
      key: 'gitBranch',
      width: 120,
      render: (branch) => branch && <Tag>{branch}</Tag>,
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags) => tags?.slice(0, 3).map((tag: string) => (
        <Tag key={tag}>{tag}</Tag>
      )),
    },
  ]

  // Add metric columns dynamically
  if (availableMetrics.length > 0) {
    availableMetrics.slice(0, 5).forEach(metricName => {
      columns.push({
        title: metricName,
        dataIndex: ['summary', metricName],
        key: metricName,
        width: 120,
        render: (value) => value != null ? Number(value).toFixed(4) : '-',
        sorter: (a, b) => {
          const aVal = a.summary[metricName] ?? -Infinity
          const bVal = b.summary[metricName] ?? -Infinity
          return aVal - bVal
        },
      })
    })
  }

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space direction="vertical" size={0}>
              <h2 style={{ margin: 0 }}>
                <CompareOutlined /> Run Comparison
              </h2>
              <span style={{ color: '#999' }}>
                Compare metrics and configurations across multiple runs
              </span>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                mode="multiple"
                placeholder="Select runs to compare"
                style={{ minWidth: 400 }}
                value={selectedRunIds}
                onChange={handleRunSelect}
                maxTagCount="responsive"
                loading={runsLoading}
              >
                {runsData?.items?.map(run => (
                  <Option key={run.id} value={run.id}>
                    {run.name || run.id.substring(0, 8)} ({run.state})
                  </Option>
                ))}
              </Select>
              <Button onClick={handleClearSelection}>Clear</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {selectedRunIds.length === 0 ? (
        <Card>
          <Empty
            description={
              <Space direction="vertical">
                <span>No runs selected for comparison</span>
                <span style={{ fontSize: 12, color: '#999' }}>
                  Select 2 or more runs from the dropdown above to compare
                </span>
              </Space>
            }
          />
        </Card>
      ) : (
        <>
          {/* Statistics Summary */}
          <Card title="Summary Statistics" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="Runs Selected"
                  value={selectedRunIds.length}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Metrics Tracked"
                  value={availableMetrics.length}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Avg Duration"
                  value={comparisonData.length > 0
                    ? dayjs.duration(
                        comparisonData.reduce((sum, r) => sum + r.durationMs, 0) / comparisonData.length
                      ).format('HH:mm:ss')
                    : '-'
                  }
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Success Rate"
                  value={comparisonData.length > 0
                    ? `${((comparisonData.filter(r => r.state === 'finished').length / comparisonData.length) * 100).toFixed(1)}%`
                    : '-'}
                />
              </Col>
            </Row>
          </Card>

          {/* Comparison Table */}
          <Card title="Run Details" style={{ marginBottom: 24 }}>
            <Table
              columns={columns}
              dataSource={comparisonData}
              pagination={false}
              scroll={{ x: 'max-content' }}
            />
          </Card>

          {/* Metric Comparison Charts */}
          {availableMetrics.length > 0 && (
            <Card title="Metric Comparison">
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Select
                  placeholder="Select a metric to visualize"
                  style={{ width: 300 }}
                  value={selectedMetric}
                  onChange={setSelectedMetric}
                >
                  {availableMetrics.map(metric => (
                    <Option key={metric} value={metric}>
                      {metric}
                    </Option>
                  ))}
                </Select>

                {selectedMetric ? (
                  <div>
                    {/* Placeholder for actual metric visualization */}
                    <Empty
                      description="Metric history charts will be available when metric data is loaded"
                    />
                  </div>
                ) : (
                  <Empty description="Select a metric to visualize" />
                )}
              </Space>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export default RunComparePage
