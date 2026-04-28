import React, { useState } from 'react'
import { Card, Button, Progress, Space, message } from 'antd'
import { PlayCircleOutlined, DownloadOutlined, LoadingOutlined } from '@ant-design/icons'
import { remotionApi } from '../../services/remotionApi'

interface EffectRenderProps {
  projectId?: string
  params?: Record<string, any>
}

const EffectRender: React.FC<EffectRenderProps> = ({ projectId, params }) => {
  const [loading, setLoading] = useState(false)
  const [job, setJob] = useState<any>(null)
  const [polling, setPolling] = useState(false)

  const handleRender = async () => {
    if (!projectId) {
      message.error('请先选择特效')
      return
    }

    try {
      setLoading(true)
      const response = await remotionApi.createRenderJob(projectId, params || {})
      if (response.success) {
        message.success('渲染任务已创建')
        setJob({ id: response.jobId, status: 'pending', progress: 0 })
        pollJobStatus(response.jobId)
      }
    } catch (error) {
      message.error('创建渲染任务失败')
    } finally {
      setLoading(false)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    setPolling(true)
    const interval = setInterval(async () => {
      try {
        const jobData = await remotionApi.getJobStatus(jobId)
        setJob(jobData)

        if (jobData.status === 'completed') {
          clearInterval(interval)
          setPolling(false)
          message.success('渲染完成')
        } else if (jobData.status === 'failed') {
          clearInterval(interval)
          setPolling(false)
          message.error(`渲染失败: ${jobData.error}`)
        }
      } catch (error) {
        clearInterval(interval)
        setPolling(false)
      }
    }, 10000)
  }

  const handleDownload = async () => {
    if (!job || !job.id) {
      message.error('没有可下载的视频')
      return
    }

    try {
      const blob = await remotionApi.downloadJobOutput(job.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `remotion_${job.id}.mp4`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      message.success('下载成功')
    } catch (error) {
      message.error('下载失败')
    }
  }

  return (
    <Card title="渲染与下载">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRender}
          loading={loading}
          block
          size="large"
        >
          开始渲染
        </Button>

        {job && (
          <>
            <div>
              <div style={{ marginBottom: 8 }}>
                <strong>任务状态：</strong>
                <span style={{ marginLeft: 8 }}>
                  {job.status === 'pending' && '等待中'}
                  {job.status === 'rendering' && '渲染中'}
                  {job.status === 'completed' && '已完成'}
                  {job.status === 'failed' && '失败'}
                </span>
              </div>
              <Progress
                percent={Math.round(job.progress * 100)}
                status={job.status === 'failed' ? 'exception' : 'active'}
              />
            </div>

            {job.status === 'completed' && (
              <Button
                type="default"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                block
                size="large"
              >
                下载视频
              </Button>
            )}

            {job.status === 'failed' && job.error && (
              <div style={{ color: '#ff4d4f' }}>
                <strong>错误信息：</strong>
                <p>{job.error}</p>
              </div>
            )}
          </>
        )}

        {polling && (
          <div style={{ textAlign: 'center', color: '#999' }}>
            <LoadingOutlined /> 正在渲染中...
          </div>
        )}
      </Space>
    </Card>
  )
}

export default EffectRender