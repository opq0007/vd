import React from 'react'
import { Card, Button, Space } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

interface PageContainerProps {
  title?: string
  extra?: React.ReactNode
  loading?: boolean
  onRefresh?: () => void
  children: React.ReactNode
}

const PageContainer: React.FC<PageContainerProps> = ({
  title,
  extra,
  loading,
  onRefresh,
  children,
}) => {
  return (
    <Card
      title={title}
      extra={
        <Space>
          {onRefresh && (
            <Button
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
            >
              刷新
            </Button>
          )}
          {extra}
        </Space>
      }
      loading={loading}
    >
      {children}
    </Card>
  )
}

export default PageContainer