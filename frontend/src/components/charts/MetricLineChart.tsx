import { useMemo } from 'react'
import { Card, Empty, Spin } from 'antd'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import dayjs from 'dayjs'
import type { Metric } from '@/types'

interface MetricLineChartProps {
  title: string
  metrics: Metric[]
  loading?: boolean
  height?: number
  showLegend?: boolean
  yAxisLabel?: string
  xAxisKey?: 'time' | 'step'
}

function MetricLineChart({
  title,
  metrics,
  loading = false,
  height = 300,
  showLegend = true,
  yAxisLabel,
  xAxisKey = 'step',
}: MetricLineChartProps) {
  // Group metrics by metric_name
  const chartData = useMemo(() => {
    if (!metrics || metrics.length === 0) return { data: [], metricNames: [] }

    // Sort by time or step
    const sorted = [...metrics].sort((a, b) => {
      if (xAxisKey === 'time') {
        return new Date(a.time).getTime() - new Date(b.time).getTime()
      }
      return (a.step || 0) - (b.step || 0)
    })

    // Get unique metric names
    const metricNames = [...new Set(sorted.map((m) => m.metric_name))]

    // Transform data for Recharts
    const dataMap = new Map<string | number, any>()

    sorted.forEach((metric) => {
      const key = xAxisKey === 'time' ? metric.time : metric.step || 0

      if (!dataMap.has(key)) {
        dataMap.set(key, {
          [xAxisKey]: key,
        })
      }

      const point = dataMap.get(key)!
      point[metric.metric_name] = metric.value
    })

    return {
      data: Array.from(dataMap.values()),
      metricNames,
    }
  }, [metrics, xAxisKey])

  const colors = [
    '#1890ff', // blue
    '#52c41a', // green
    '#faad14', // orange
    '#f5222d', // red
    '#722ed1', // purple
    '#13c2c2', // cyan
    '#eb2f96', // magenta
    '#fa8c16', // volcano
  ]

  const formatXAxis = (value: any) => {
    if (xAxisKey === 'time') {
      return dayjs(value).format('HH:mm:ss')
    }
    return value
  }

  const formatTooltipLabel = (value: any) => {
    if (xAxisKey === 'time') {
      return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
    }
    return `Step: ${value}`
  }

  return (
    <Card title={title} bordered={false}>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
        </div>
      ) : chartData.data.length === 0 ? (
        <Empty description="No metrics data" style={{ padding: '100px 0' }} />
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxisKey} tickFormatter={formatXAxis} />
            <YAxis label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined} />
            <Tooltip labelFormatter={formatTooltipLabel} />
            {showLegend && <Legend />}
            {chartData.metricNames.map((name, index) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={colors[index % colors.length]}
                dot={false}
                strokeWidth={2}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  )
}

export default MetricLineChart
