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
  Modal,
  Form,
  Input,
  Upload,
  message,
  Progress,
  Popconfirm,
} from 'antd'
import {
  ArrowLeftOutlined,
  DatabaseOutlined,
  FolderOutlined,
  FileOutlined,
  CodeOutlined,
  PlusOutlined,
  UploadOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  LockOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import type { ColumnsType } from 'antd/es/table'
import type {
  ArtifactType,
  ArtifactVersion,
  ArtifactFile,
  ArtifactVersionFormData,
} from '@/types'
import {
  useGetArtifactQuery,
  useListArtifactVersionsQuery,
  useGetArtifactVersionQuery,
  useCreateArtifactVersionMutation,
  useFinalizeVersionMutation,
  useGetFileUploadUrlMutation,
  useAddFileToVersionMutation,
  useLazyGetFileDownloadUrlQuery,
  useDeleteFileMutation,
} from '@/services/artifactsApi'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

const artifactTypeConfig = {
  model: { color: 'purple', icon: <DatabaseOutlined />, label: 'Model' },
  dataset: { color: 'blue', icon: <FolderOutlined />, label: 'Dataset' },
  file: { color: 'green', icon: <FileOutlined />, label: 'File' },
  code: { color: 'orange', icon: <CodeOutlined />, label: 'Code' },
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}

function ArtifactDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [selectedVersionId, setSelectedVersionId] = useState<string>()
  const [isVersionModalOpen, setIsVersionModalOpen] = useState(false)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [form] = Form.useForm()
  const [uploadForm] = Form.useForm()

  const { data: artifact, isLoading } = useGetArtifactQuery(id!)
  const { data: versionsData } = useListArtifactVersionsQuery(
    { artifactId: id! },
    { skip: !id }
  )
  const { data: selectedVersion } = useGetArtifactVersionQuery(selectedVersionId!, {
    skip: !selectedVersionId,
  })

  const [createVersion, { isLoading: isCreatingVersion }] = useCreateArtifactVersionMutation()
  const [finalizeVersion] = useFinalizeVersionMutation()
  const [getUploadUrl] = useGetFileUploadUrlMutation()
  const [addFile] = useAddFileToVersionMutation()
  const [getDownloadUrl] = useLazyGetFileDownloadUrlQuery()
  const [deleteFile] = useDeleteFileMutation()

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!artifact) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Empty description="Artifact not found" />
      </div>
    )
  }

  const config = artifactTypeConfig[artifact.type as ArtifactType]

  const handleCreateVersion = async (values: ArtifactVersionFormData) => {
    try {
      const version = await createVersion({
        artifactId: id!,
        data: { ...values, artifactId: id! },
      }).unwrap()
      message.success('Version created successfully')
      setIsVersionModalOpen(false)
      form.resetFields()
      setSelectedVersionId(version.id)
      setActiveTab('versions')
    } catch (error) {
      message.error('Failed to create version')
    }
  }

  const handleFinalizeVersion = async (versionId: string) => {
    try {
      await finalizeVersion({ versionId }).unwrap()
      message.success('Version finalized successfully')
    } catch (error) {
      message.error('Failed to finalize version')
    }
  }

  const handleFileUpload = async (values: { files: any[] }) => {
    if (!selectedVersionId) {
      message.error('Please select a version first')
      return
    }

    try {
      setUploadProgress(0)
      const files = values.files

      for (let i = 0; i < files.length; i++) {
        const file = files[i].originFileObj
        const fileName = file.name

        // Get upload URL
        const { uploadUrl, storageKey } = await getUploadUrl({
          versionId: selectedVersionId,
          request: { path: fileName },
        }).unwrap()

        // Upload to MinIO
        await fetch(uploadUrl, {
          method: 'PUT',
          body: file,
          headers: {
            'Content-Type': file.type || 'application/octet-stream',
          },
        })

        // Register file in database
        await addFile({
          versionId: selectedVersionId,
          file: {
            path: fileName,
            name: fileName,
            size: file.size,
            storageKey,
            mimeType: file.type || undefined,
          },
        }).unwrap()

        setUploadProgress(((i + 1) / files.length) * 100)
      }

      message.success('Files uploaded successfully')
      setIsUploadModalOpen(false)
      uploadForm.resetFields()
      setUploadProgress(0)
    } catch (error) {
      message.error('Failed to upload files')
      setUploadProgress(0)
    }
  }

  const handleDownloadFile = async (fileId: string, fileName: string) => {
    try {
      const { downloadUrl } = await getDownloadUrl(fileId).unwrap()

      // Download file
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      message.success('Download started')
    } catch (error) {
      message.error('Failed to download file')
    }
  }

  const versionColumns: ColumnsType<ArtifactVersion> = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      render: (text, record) => (
        <Space>
          <a onClick={() => setSelectedVersionId(record.id)}>{text}</a>
          {record.isFinalized && (
            <Tag color="green" icon={<LockOutlined />}>
              Finalized
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <span style={{ color: '#999' }}>No description</span>,
    },
    {
      title: 'Files',
      dataIndex: 'fileCount',
      key: 'fileCount',
      width: 80,
      align: 'center',
    },
    {
      title: 'Size',
      dataIndex: 'totalSize',
      key: 'totalSize',
      width: 120,
      render: (size: number) => formatBytes(size),
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
      render: (date: string) => dayjs(date).fromNow(),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => setSelectedVersionId(record.id)}
          >
            View
          </Button>
          {!record.isFinalized && (
            <Popconfirm
              title="Finalize version"
              description="Are you sure? This action cannot be undone."
              onConfirm={() => handleFinalizeVersion(record.id)}
            >
              <Button type="link" size="small">
                Finalize
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const fileColumns: ColumnsType<ArtifactFile> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Space>
          <FileOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Path',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
    },
    {
      title: 'Size',
      dataIndex: 'size',
      key: 'size',
      width: 120,
      render: (size: number) => formatBytes(size),
    },
    {
      title: 'Type',
      dataIndex: 'mimeType',
      key: 'mimeType',
      width: 150,
      render: (type) => type || <span style={{ color: '#999' }}>Unknown</span>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadFile(record.id, record.name)}
          >
            Download
          </Button>
          {selectedVersion && !selectedVersion.isFinalized && (
            <Popconfirm
              title="Delete file"
              description="Are you sure you want to delete this file?"
              onConfirm={async () => {
                try {
                  await deleteFile(record.id).unwrap()
                  message.success('File deleted')
                } catch (error) {
                  message.error('Failed to delete file')
                }
              }}
            >
              <Button type="link" danger size="small">
                Delete
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
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
              {artifact.name}
            </Title>
            <Space size={8}>
              <Tag color={config.color} icon={config.icon}>
                {config.label}
              </Tag>
              {artifact.tags?.map(tag => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setIsVersionModalOpen(true)}
            >
              New Version
            </Button>
          </Space>
        </div>
      </div>

      {/* Tabs */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Overview" key="overview">
          <Card>
            <Descriptions column={2} bordered>
              <Descriptions.Item label="ID">{artifact.id}</Descriptions.Item>
              <Descriptions.Item label="Type">
                <Tag color={config.color} icon={config.icon}>
                  {config.label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Versions">
                {artifact.versionCount}
              </Descriptions.Item>
              <Descriptions.Item label="Latest Version">
                {artifact.latestVersion || 'None'}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {dayjs(artifact.createdAt).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="Updated">
                {dayjs(artifact.updatedAt).fromNow()}
              </Descriptions.Item>
              <Descriptions.Item label="Description" span={2}>
                {artifact.description || (
                  <Text type="secondary">No description</Text>
                )}
              </Descriptions.Item>
              {artifact.tags && artifact.tags.length > 0 && (
                <Descriptions.Item label="Tags" span={2}>
                  <Space wrap>
                    {artifact.tags.map(tag => (
                      <Tag key={tag}>{tag}</Tag>
                    ))}
                  </Space>
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={`Versions (${artifact.versionCount})`} key="versions">
          <Card
            extra={
              selectedVersionId && (
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => setIsUploadModalOpen(true)}
                  disabled={selectedVersion?.isFinalized}
                >
                  Upload Files
                </Button>
              )
            }
          >
            <Table
              columns={versionColumns}
              dataSource={versionsData?.items || []}
              rowKey="id"
              pagination={false}
            />

            {selectedVersion && (
              <Card
                title={`Version ${selectedVersion.version} Files`}
                style={{ marginTop: 16 }}
                extra={
                  selectedVersion.isFinalized ? (
                    <Tag color="green" icon={<CheckCircleOutlined />}>
                      Finalized
                    </Tag>
                  ) : (
                    <Tag color="orange">Draft</Tag>
                  )
                }
              >
                {selectedVersion.description && (
                  <p style={{ marginBottom: 16 }}>
                    <Text type="secondary">{selectedVersion.description}</Text>
                  </p>
                )}
                <Table
                  columns={fileColumns}
                  dataSource={selectedVersion.files || []}
                  rowKey="id"
                  pagination={false}
                />
              </Card>
            )}
          </Card>
        </Tabs.TabPane>
      </Tabs>

      {/* Create Version Modal */}
      <Modal
        title="Create New Version"
        open={isVersionModalOpen}
        onCancel={() => {
          setIsVersionModalOpen(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        confirmLoading={isCreatingVersion}
      >
        <Form form={form} layout="vertical" onFinish={handleCreateVersion}>
          <Form.Item label="Version" name="version">
            <Input placeholder="v1.0.0 (leave empty for auto-increment)" />
          </Form.Item>

          <Form.Item label="Description" name="description">
            <Input.TextArea rows={3} placeholder="Describe this version..." />
          </Form.Item>

          <Form.Item label="Notes" name="notes">
            <Input.TextArea rows={2} placeholder="Additional notes..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Upload Files Modal */}
      <Modal
        title="Upload Files"
        open={isUploadModalOpen}
        onCancel={() => {
          setIsUploadModalOpen(false)
          uploadForm.resetFields()
          setUploadProgress(0)
        }}
        onOk={() => uploadForm.submit()}
        confirmLoading={uploadProgress > 0}
      >
        <Form form={uploadForm} layout="vertical" onFinish={handleFileUpload}>
          <Form.Item
            label="Files"
            name="files"
            valuePropName="fileList"
            getValueFromEvent={(e) => {
              if (Array.isArray(e)) {
                return e
              }
              return e?.fileList
            }}
            rules={[{ required: true, message: 'Please select files to upload' }]}
          >
            <Upload.Dragger
              multiple
              beforeUpload={() => false}
              listType="text"
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">Click or drag files to this area</p>
              <p className="ant-upload-hint">
                Support for single or bulk upload
              </p>
            </Upload.Dragger>
          </Form.Item>

          {uploadProgress > 0 && (
            <Progress percent={Math.round(uploadProgress)} status="active" />
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default ArtifactDetailPage
