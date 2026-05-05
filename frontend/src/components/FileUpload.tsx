import React, { useCallback } from 'react'
import { Upload, message } from 'antd'
import type { UploadProps } from 'antd'

interface FileUploadProps {
  accept?: string
  maxSize?: number
  onFileSelect?: (file: File) => void
  onUploadProgress?: (progress: number) => void
  children?: React.ReactNode
}

const FileUpload: React.FC<FileUploadProps> = ({
  accept = '*',
  maxSize = 50 * 1024 * 1024,
  onFileSelect,
  onUploadProgress,
  children,
}) => {
  const beforeUpload = useCallback(
    (file: File) => {
      const isValidSize = file.size <= maxSize
      if (!isValidSize) {
        message.error(`文件大小不能超过 ${(maxSize / 1024 / 1024).toFixed(0)}MB`)
        return false
      }

      if (onFileSelect) {
        onFileSelect(file)
      }

      return false
    },
    [maxSize, onFileSelect]
  )

  const uploadProps: UploadProps = {
    name: 'file',
    accept,
    beforeUpload,
    showUploadList: false,
    customRequest: ({ onProgress, onSuccess, onError, file }) => {
      const reader = new FileReader()

      reader.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100)
          onUploadProgress?.(percent)
        }
      }

      reader.onload = () => {
        onSuccess?.(reader.result)
      }

      reader.onerror = () => {
        onError?.(new Error('文件读取失败'))
      }

      reader.readAsDataURL(file as File)
    },
  }

  return (
    <Upload {...uploadProps}>
      <div className="upload-area">
        {children || (
          <div>
            <p className="ant-upload-drag-icon">
              <span style={{ fontSize: 48 }}>📁</span>
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此处上传</p>
            <p className="ant-upload-hint">
              支持单个文件上传，最大 {(maxSize / 1024 / 1024).toFixed(0)}MB
            </p>
          </div>
        )}
      </div>
    </Upload>
  )
}

export default FileUpload