import { useMemo } from 'react'
import { Card, Empty, Spin } from 'antd'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { Run } from '@/types'

interface MetricComparisonChartProps {
  title: string
  runs: Run[]
  metricName: string
  loading?: boolean
  height?: number
}

// This component will be used for comparing the same metric across multiple runs
function MetricComparisonChart({ title, runs, metricName, loading = false, height = 300 }: MetricComparisonChartProps) {
  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

  if (loading) {
    return (
      <Card title={title} bordered={false}>
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
        </div>
      </Card>
    )
  }

  if (!runs || runs.length === 0) {
    return (
      <Card title={title} bordered={false}>
        <Empty description="No runs selected for comparison" style={{ padding: '100px 0' }} />
      </Card>
    )
  }

  return (
    <Card title={title} bordered={false}>
      <Empty description="Comparison chart will be implemented when metric data is available" style={{ padding: '100px 0' }} />
    </Card>
  )
}

export default MetricComparisonChart
