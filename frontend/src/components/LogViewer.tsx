import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  Card,
  Space,
  Select,
  Input,
  Button,
  Tag,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  Switch,
  Tooltip,
  message,
} from 'antd'
import {
  DownloadOutlined,
  ClearOutlined,
  ReloadOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import {
  useGetLatestLogsQuery,
  useGetLogsSummaryQuery,
  useLazyDownloadLogsQuery,
  useDeleteLogsMutation,
  type RunLog,
} from '@/services/runLogsApi'

const { Search } = Input

interface LogViewerProps {
  runId: string
}

// Helper function to get log level color
const getLevelColor = (level: string): string => {
  switch (level.toUpperCase()) {
    case 'DEBUG':
      return '#8c8c8c'
    case 'INFO':
      return '#52c41a'
    case 'WARNING':
      return '#faad14'
    case 'ERROR':
      return '#ff4d4f'
    default:
      return '#d4d4d4'
  }
}

// Helper function to get source color
const getSourceColor = (source: string): string => {
  switch (source.toLowerCase()) {
    case 'stdout':
      return 'blue'
    case 'stderr':
      return 'red'
    case 'sdk':
      return 'green'
    default:
      return 'default'
  }
}

function LogViewer({ runId }: LogViewerProps) {
  const [logs, setLogs] = useState<RunLog[]>([])
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [searchText, setSearchText] = useState<string>('')
  const [autoScroll, setAutoScroll] = useState<boolean>(true)
  const [isPaused, setIsPaused] = useState<boolean>(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Fetch initial logs
  const { data: initialLogs, isLoading, refetch } = useGetLatestLogsQuery({
    runId,
    limit: 500,
  })

  // Fetch summary
  const { data: summary } = useGetLogsSummaryQuery(runId)

  // Download and delete mutations
  const [downloadLogs] = useLazyDownloadLogsQuery()
  const [deleteLogs, { isLoading: isDeleting }] = useDeleteLogsMutation()

  // Initialize logs from API
  useEffect(() => {
    if (initialLogs) {
      setLogs(initialLogs)
    }
  }, [initialLogs])

  // WebSocket connection for real-time logs
  useEffect(() => {
    if (isPaused) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/runs/${runId}/logs/stream`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const log: RunLog = JSON.parse(event.data)
        setLogs((prev) => [...prev, log])
      } catch (error) {
        console.error('Failed to parse log message:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    // Ping periodically to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      ws.close()
    }
  }, [runId, isPaused])

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    if (levelFilter !== 'all' && log.level !== levelFilter) return false
    if (sourceFilter !== 'all' && log.source !== sourceFilter) return false
    if (searchText && !log.message.toLowerCase().includes(searchText.toLowerCase())) {
      return false
    }
    return true
  })

  // Handle download
  const handleDownload = async (format: 'txt' | 'json' | 'csv' = 'txt') => {
    try {
      await downloadLogs({
        runId,
        format,
        level: levelFilter !== 'all' ? levelFilter : undefined,
        source: sourceFilter !== 'all' ? sourceFilter : undefined,
        search: searchText || undefined,
      })
      message.success(`Downloading logs as ${format.toUpperCase()}...`)
    } catch (error: any) {
      message.error('Failed to download logs')
    }
  }

  // Handle clear
  const handleClear = async () => {
    try {
      await deleteLogs(runId).unwrap()
      setLogs([])
      message.success('Logs cleared successfully')
      refetch()
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to clear logs')
    }
  }

  // Handle refresh
  const handleRefresh = () => {
    refetch()
  }

  // Toggle pause/resume
  const togglePause = () => {
    setIsPaused(!isPaused)
  }

  if (isLoading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" tip="Loading logs..." />
        </div>
      </Card>
    )
  }

  return (
    <Card>
      {/* Summary Statistics */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Statistic title="Total Logs" value={summary.total} />
          </Col>
          {summary.byLevel.DEBUG !== undefined && (
            <Col span={4}>
              <Statistic
                title="Debug"
                value={summary.byLevel.DEBUG}
                valueStyle={{ color: '#8c8c8c' }}
              />
            </Col>
          )}
          {summary.byLevel.INFO !== undefined && (
            <Col span={4}>
              <Statistic
                title="Info"
                value={summary.byLevel.INFO}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
          )}
          {summary.byLevel.WARNING !== undefined && (
            <Col span={4}>
              <Statistic
                title="Warning"
                value={summary.byLevel.WARNING}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
          )}
          {summary.byLevel.ERROR !== undefined && (
            <Col span={4}>
              <Statistic
                title="Error"
                value={summary.byLevel.ERROR}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          )}
        </Row>
      )}

      {/* Toolbar */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Select
            value={levelFilter}
            onChange={setLevelFilter}
            style={{ width: 120 }}
            placeholder="Level"
          >
            <Select.Option value="all">All Levels</Select.Option>
            <Select.Option value="DEBUG">Debug</Select.Option>
            <Select.Option value="INFO">Info</Select.Option>
            <Select.Option value="WARNING">Warning</Select.Option>
            <Select.Option value="ERROR">Error</Select.Option>
          </Select>

          <Select
            value={sourceFilter}
            onChange={setSourceFilter}
            style={{ width: 120 }}
            placeholder="Source"
          >
            <Select.Option value="all">All Sources</Select.Option>
            <Select.Option value="stdout">stdout</Select.Option>
            <Select.Option value="stderr">stderr</Select.Option>
            <Select.Option value="sdk">SDK</Select.Option>
          </Select>

          <Search
            placeholder="Search logs..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
        </Space>

        <Space>
          <Tooltip title={isPaused ? 'Resume real-time updates' : 'Pause real-time updates'}>
            <Button
              icon={isPaused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={togglePause}
              type={isPaused ? 'primary' : 'default'}
            >
              {isPaused ? 'Resume' : 'Pause'}
            </Button>
          </Tooltip>

          <Tooltip title="Refresh logs">
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} />
          </Tooltip>

          <Tooltip title="Download logs">
            <Button.Group>
              <Button icon={<DownloadOutlined />} onClick={() => handleDownload('txt')}>
                TXT
              </Button>
              <Button onClick={() => handleDownload('json')}>JSON</Button>
              <Button onClick={() => handleDownload('csv')}>CSV</Button>
            </Button.Group>
          </Tooltip>

          <Tooltip title="Clear all logs">
            <Button
              icon={<ClearOutlined />}
              onClick={handleClear}
              danger
              loading={isDeleting}
            >
              Clear
            </Button>
          </Tooltip>

          <span>
            Auto-scroll:
            <Switch
              checked={autoScroll}
              onChange={setAutoScroll}
              style={{ marginLeft: 8 }}
            />
          </span>
        </Space>
      </Space>

      {/* Log display */}
      {filteredLogs.length === 0 ? (
        <Empty description="No logs found" style={{ padding: 48 }} />
      ) : (
        <div
          ref={containerRef}
          style={{
            height: 600,
            overflow: 'auto',
            backgroundColor: '#1e1e1e',
            color: '#d4d4d4',
            fontFamily: '"Courier New", Courier, monospace',
            fontSize: '13px',
            padding: 16,
            borderRadius: 4,
            lineHeight: '1.6',
          }}
        >
          {filteredLogs.map((log, idx) => (
            <div
              key={`${log.id}-${idx}`}
              style={{
                marginBottom: 2,
                paddingLeft: 4,
                paddingRight: 4,
                wordWrap: 'break-word',
                whiteSpace: 'pre-wrap',
              }}
            >
              <span style={{ color: '#666', marginRight: 8 }}>
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span
                style={{
                  color: getLevelColor(log.level),
                  marginRight: 8,
                  fontWeight: 'bold',
                  minWidth: '60px',
                  display: 'inline-block',
                }}
              >
                [{log.level}]
              </span>
              <span style={{ color: '#888', marginRight: 8 }}>
                <Tag color={getSourceColor(log.source)} style={{ fontSize: '11px' }}>
                  {log.source}
                </Tag>
              </span>
              <span>{log.message}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 8, color: '#8c8c8c', fontSize: '12px' }}>
        Showing {filteredLogs.length} of {logs.length} logs
        {isPaused && (
          <Tag color="orange" style={{ marginLeft: 8 }}>
            Real-time updates paused
          </Tag>
        )}
      </div>
    </Card>
  )
}

export default LogViewer
