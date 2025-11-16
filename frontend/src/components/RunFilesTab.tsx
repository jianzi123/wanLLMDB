import { useState } from 'react'
import {
  Table,
  Button,
  Space,
  message,
  Popconfirm,
  Tag,
  Typography,
  Empty,
  Card,
} from 'antd'
import {
  DownloadOutlined,
  DeleteOutlined,
  FileOutlined,
  FileTextOutlined,
  FileImageOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  FileWordOutlined,
  FileZipOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  useListRunFilesQuery,
  useDeleteRunFileMutation,
  useLazyGetFileDownloadUrlQuery,
  type RunFile,
} from '@/services/runFilesApi'

const { Text } = Typography

interface RunFilesTabProps {
  runId: string
}

// Helper function to get file icon based on content type
const getFileIcon = (contentType?: string, filename?: string) => {
  if (!contentType && filename) {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'txt':
      case 'md':
      case 'log':
        return <FileTextOutlined />
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        return <FileImageOutlined />
      case 'pdf':
        return <FilePdfOutlined />
      case 'xls':
      case 'xlsx':
      case 'csv':
        return <FileExcelOutlined />
      case 'doc':
      case 'docx':
        return <FileWordOutlined />
      case 'zip':
      case 'tar':
      case 'gz':
        return <FileZipOutlined />
      default:
        return <FileOutlined />
    }
  }

  if (contentType?.startsWith('text/')) return <FileTextOutlined />
  if (contentType?.startsWith('image/')) return <FileImageOutlined />
  if (contentType === 'application/pdf') return <FilePdfOutlined />
  if (
    contentType === 'application/vnd.ms-excel' ||
    contentType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
    contentType === 'text/csv'
  )
    return <FileExcelOutlined />
  if (
    contentType === 'application/msword' ||
    contentType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  )
    return <FileWordOutlined />
  if (
    contentType === 'application/zip' ||
    contentType === 'application/x-tar' ||
    contentType === 'application/gzip'
  )
    return <FileZipOutlined />

  return <FileOutlined />
}

// Helper function to format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function RunFilesTab({ runId }: RunFilesTabProps) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const { data, isLoading, refetch } = useListRunFilesQuery({
    runId,
    skip: (page - 1) * pageSize,
    limit: pageSize,
  })

  const [deleteFile] = useDeleteRunFileMutation()
  const [getDownloadUrl] = useLazyGetFileDownloadUrlQuery()

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const response = await getDownloadUrl(fileId).unwrap()

      // Download file using the presigned URL
      const link = document.createElement('a')
      link.href = response.downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      message.success(`Downloading ${filename}...`)
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to download file')
    }
  }

  const handleDelete = async (fileId: string, filename: string) => {
    try {
      await deleteFile(fileId).unwrap()
      message.success(`Deleted ${filename}`)
      refetch()
    } catch (error: any) {
      message.error(error?.data?.detail || 'Failed to delete file')
    }
  }

  const columns: ColumnsType<RunFile> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          {getFileIcon(record.contentType, name)}
          <Text strong>{name}</Text>
        </Space>
      ),
      width: '30%',
    },
    {
      title: 'Path',
      dataIndex: 'path',
      key: 'path',
      render: path => <Text type="secondary">{path}</Text>,
      width: '25%',
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      render: size => formatFileSize(size),
      width: '10%',
      sorter: (a, b) => a.size - b.size,
    },
    {
      title: 'Type',
      dataIndex: 'contentType',
      key: 'contentType',
      render: contentType => (
        <Tag>{contentType || 'unknown'}</Tag>
      ),
      width: '15%',
    },
    {
      title: 'Uploaded',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: createdAt => dayjs(createdAt).format('YYYY-MM-DD HH:mm:ss'),
      width: '15%',
      sorter: (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record.id, record.name)}
            size="small"
          >
            Download
          </Button>
          <Popconfirm
            title="Delete file"
            description="Are you sure you want to delete this file?"
            onConfirm={() => handleDelete(record.id, record.name)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />} size="small">
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
      width: '5%',
    },
  ]

  if (!data?.items?.length && !isLoading) {
    return (
      <Card>
        <Empty
          description={
            <div>
              <p>No files uploaded yet</p>
              <Text type="secondary">
                Files can be uploaded using <Text code>wandb.save()</Text> in your code
              </Text>
            </div>
          }
        />
      </Card>
    )
  }

  return (
    <Card>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>Total Files:</Text>
          <Tag color="blue">{data?.total || 0}</Tag>
          {data?.items && (
            <>
              <Text strong>Total Size:</Text>
              <Tag color="green">
                {formatFileSize(data.items.reduce((sum, file) => sum + file.size, 0))}
              </Tag>
            </>
          )}
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: total => `Total ${total} files`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage)
            setPageSize(newPageSize)
          },
        }}
      />
    </Card>
  )
}

export default RunFilesTab
