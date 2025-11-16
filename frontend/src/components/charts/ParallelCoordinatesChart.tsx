import { useMemo } from 'react'
import { Card, Empty, Tag } from 'antd'
import type { ParallelCoordinatesData } from '@/types'

interface ParallelCoordinatesChartProps {
  data: ParallelCoordinatesData
  height?: number
}

/**
 * Parallel Coordinates Chart Component
 *
 * Visualizes high-dimensional data by showing each data point as a line
 * crossing through multiple parallel axes (one per dimension).
 *
 * This is a simplified implementation using SVG. For production, consider
 * using D3.js or Plotly for more advanced features.
 */
function ParallelCoordinatesChart({
  data,
  height = 400,
}: ParallelCoordinatesChartProps) {
  const { dimensions, data: runs, bestIndex } = data

  // Calculate scales for each dimension
  const scales = useMemo(() => {
    if (!dimensions.length || !runs.length) return {}

    const result: Record<string, { min: number; max: number }> = {}

    dimensions.forEach(dim => {
      const values = runs
        .map(run => run[dim])
        .filter(v => typeof v === 'number') as number[]

      if (values.length > 0) {
        result[dim] = {
          min: Math.min(...values),
          max: Math.max(...values),
        }
      }
    })

    return result
  }, [dimensions, runs])

  // Normalize value to 0-1 range
  const normalize = (value: number, dim: string): number => {
    const scale = scales[dim]
    if (!scale) return 0.5

    const range = scale.max - scale.min
    if (range === 0) return 0.5

    return (value - scale.min) / range
  }

  // Calculate SVG dimensions
  const padding = { top: 40, right: 40, bottom: 40, left: 40 }
  const width = 800
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  // Calculate axis positions
  const axisSpacing = chartWidth / (dimensions.length - 1 || 1)
  const axisPositions = dimensions.map((_, i) => padding.left + i * axisSpacing)

  if (!dimensions.length || !runs.length) {
    return (
      <Card>
        <Empty description="No data available for visualization" />
      </Card>
    )
  }

  // Generate path for a single run
  const generatePath = (run: Record<string, any>, index: number): string => {
    const points = dimensions.map((dim, i) => {
      const value = run[dim]
      if (typeof value !== 'number') return null

      const x = axisPositions[i]
      const y = padding.top + chartHeight * (1 - normalize(value, dim))

      return `${x},${y}`
    }).filter(Boolean)

    return `M ${points.join(' L ')}`
  }

  return (
    <Card title="Parameter Space Visualization">
      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        {/* Axes */}
        {dimensions.map((dim, i) => {
          const x = axisPositions[i]
          const scale = scales[dim]

          return (
            <g key={dim}>
              {/* Axis line */}
              <line
                x1={x}
                y1={padding.top}
                x2={x}
                y2={padding.top + chartHeight}
                stroke="#d9d9d9"
                strokeWidth={2}
              />

              {/* Axis label */}
              <text
                x={x}
                y={padding.top - 10}
                textAnchor="middle"
                fontSize={12}
                fontWeight="bold"
                fill="#262626"
              >
                {dim}
              </text>

              {/* Scale labels */}
              {scale && (
                <>
                  <text
                    x={x + 5}
                    y={padding.top + 5}
                    fontSize={10}
                    fill="#8c8c8c"
                  >
                    {scale.max.toFixed(4)}
                  </text>
                  <text
                    x={x + 5}
                    y={padding.top + chartHeight - 5}
                    fontSize={10}
                    fill="#8c8c8c"
                  >
                    {scale.min.toFixed(4)}
                  </text>
                </>
              )}
            </g>
          )
        })}

        {/* Data lines */}
        {runs.map((run, index) => {
          const isBest = index === bestIndex
          const path = generatePath(run, index)

          return (
            <path
              key={index}
              d={path}
              fill="none"
              stroke={isBest ? '#faad14' : '#1890ff'}
              strokeWidth={isBest ? 3 : 1}
              strokeOpacity={isBest ? 0.9 : 0.3}
              style={{
                transition: 'stroke-opacity 0.2s',
              }}
              onMouseEnter={(e) => {
                const target = e.target as SVGPathElement
                target.style.strokeOpacity = '1'
                target.style.strokeWidth = isBest ? '4' : '2'
              }}
              onMouseLeave={(e) => {
                const target = e.target as SVGPathElement
                target.style.strokeOpacity = isBest ? '0.9' : '0.3'
                target.style.strokeWidth = isBest ? '3' : '1'
              }}
            />
          )
        })}
      </svg>

      {/* Legend */}
      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Tag color="blue">All Runs</Tag>
        <Tag color="gold">Best Run</Tag>
        <span style={{ marginLeft: 16, color: '#8c8c8c', fontSize: 12 }}>
          Hover over lines to highlight
        </span>
      </div>
    </Card>
  )
}

export default ParallelCoordinatesChart
