import React, { useState } from 'react'
import { Table, Button, message, Space, Tag } from 'antd'
import { CloudUploadOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons'
import FileUpload from '../components/FileUpload'

interface FileRecord {
  id: string
  name: string
  size: number
  type: string
  url: string
  uploaded_at: string
}

const FilePersistence: React.FC = () => {
  const [files, setFiles] = useState<FileRecord[]>([])
  const [uploading, setUploading] = useState(false)

  const columns = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => `${(size / 1024 / 1024).toFixed(2)} MB`,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '上传时间',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: FileRecord) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => handleDownload(record)}
          >
            下载
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  const handleFileSelect = async (file: File) => {
    setUploading(true)
    try {
      const newFile: FileRecord = {
        id: Date.now().toString(),
        name: file.name,
        size: file.size,
        type: file.type || 'unknown',
        url: URL.createObjectURL(file),
        uploaded_at: new Date().toISOString(),
      }
      setFiles([...files, newFile])
      message.success('文件上传成功')
    } catch (error) {
      message.error('文件上传失败')
    } finally {
      setUploading(false)
    }
  }

  const handleDownload = (file: FileRecord) => {
    const link = document.createElement('a')
    link.href = file.url
    link.download = file.name
    link.click()
  }

  const handleDelete = (id: string) => {
    setFiles(files.filter((f) => f.id !== id))
    message.success('文件删除成功')
  }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <FileUpload
          accept="*"
          maxSize={100 * 1024 * 1024}
          onFileSelect={handleFileSelect}
        >
          <div>
            <p className="ant-upload-drag-icon">
              <CloudUploadOutlined style={{ fontSize: 48 }} />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p className="ant-upload-hint">
              支持单个文件上传，最大 100MB
            </p>
          </div>
        </FileUpload>
      </div>

      <Table
        columns={columns}
        dataSource={files}
        rowKey="id"
        loading={uploading}
      />
    </div>
  )
}

export default FilePersistence