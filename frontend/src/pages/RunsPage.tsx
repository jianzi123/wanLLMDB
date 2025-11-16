import { useState } from 'react'
import {
  Typography,
  Button,
  Table,
  Space,
  Tag,
  Select,
  Input,
  Popconfirm,
  message,
} from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import type { Run } from '@/types'
import { useListRunsQuery, useDeleteRunMutation } from '@/services/runsApi'

dayjs.extend(duration)
dayjs.extend(relativeTime)

const { Title } = Typography

const stateConfig = {
  running: { color: 'blue', icon: <PlayCircleOutlined /> },
  finished: { color: 'green', icon: <CheckCircleOutlined /> },
  crashed: { color: 'red', icon: <CloseCircleOutlined /> },
  killed: { color: 'orange', icon: <StopOutlined /> },
}

function RunsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [stateFilter, setStateFilter] = useState<string | undefined>()
  const [search, setSearch] = useState<string>()

  const { data, isLoading } = useListRunsQuery({
    page,
    pageSize,
    state: stateFilter as any,
    search,
  })
  const [deleteRun] = useDeleteRunMutation()

  const columns: ColumnsType<Run> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a onClick={() => navigate(`/runs/${record.id}`)}>
          {text || `Run ${record.id.substring(0, 8)}`}
        </a>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      width: 120,
      render: (state: string) => {
        const config = stateConfig[state as keyof typeof stateConfig]
        return (
          <Tag color={config.color} icon={config.icon}>
            {state.toUpperCase()}
          </Tag>
        )
      },
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) =>
        tags?.length > 0 ? (
          <Space size={4} wrap>
            {tags.map(tag => (
              <Tag key={tag} style={{ margin: 0 }}>
                {tag}
              </Tag>
            ))}
          </Space>
        ) : (
          <span style={{ color: '#999' }}>No tags</span>
        ),
    },
    {
      title: 'Started',
      dataIndex: 'startedAt',
      key: 'startedAt',
      width: 180,
      render: (date: string) => (
        <>
          <div>{dayjs(date).format('YYYY-MM-DD HH:mm')}</div>
          <div style={{ fontSize: 12, color: '#999' }}>
            {dayjs(date).fromNow()}
          </div>
        </>
      ),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_: any, record: Run) => {
        if (record.state === 'running') {
          const duration = dayjs().diff(dayjs(record.startedAt), 'second')
          return dayjs.duration(duration, 'seconds').format('HH:mm:ss')
        }
        if (record.finishedAt) {
          const duration = dayjs(record.finishedAt).diff(
            dayjs(record.startedAt),
            'second'
          )
          return dayjs.duration(duration, 'seconds').format('HH:mm:ss')
        }
        return '-'
      },
    },
    {
      title: 'Git Branch',
      dataIndex: 'gitBranch',
      key: 'gitBranch',
      ellipsis: true,
      render: (branch: string) => branch || '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      render: (_: any, record: Run) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/runs/${record.id}`)}
          >
            View
          </Button>
          <Popconfirm
            title="Delete run"
            description="Are you sure you want to delete this run?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" size="small" danger>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleDelete = async (id: string) => {
    try {
      await deleteRun(id).unwrap()
      message.success('Run deleted successfully!')
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to delete run')
    }
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <Title level={2}>Runs</Title>
      </div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <Input
          placeholder="Search runs..."
          prefix={<SearchOutlined />}
          allowClear
          style={{ width: 300 }}
          onChange={e => setSearch(e.target.value || undefined)}
        />
        <Select
          placeholder="Filter by state"
          allowClear
          style={{ width: 200 }}
          onChange={value => setStateFilter(value)}
          options={[
            { label: 'Running', value: 'running' },
            { label: 'Finished', value: 'finished' },
            { label: 'Crashed', value: 'crashed' },
            { label: 'Killed', value: 'killed' },
          ]}
        />
      </div>

      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          total: data?.meta.total || 0,
          pageSize: data?.meta.pageSize || 20,
          current: page,
          showSizeChanger: true,
          showTotal: total => `Total ${total} runs`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize || 20)
          },
        }}
      />
    </div>
  )
}

export default RunsPage
