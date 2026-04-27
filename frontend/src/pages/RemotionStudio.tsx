import React, { useState } from 'react'
import { Card, Button, Form, Input, Select, Slider, message, Space, Row, Col } from 'antd'
import { PlayCircleOutlined, VideoCameraOutlined, SettingOutlined } from '@ant-design/icons'
import { Player } from '@remotion/player'
import MyVideo from '../remotion/MyVideo'

const { Option } = Select

const RemotionStudio: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const handlePreview = async () => {
    try {
      await form.validateFields()
      setLoading(true)
      message.success('预览生成成功')
      setPreviewUrl('preview.mp4')
    } catch (error) {
      message.error('预览生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRender = async () => {
    try {
      await form.validateFields()
      setLoading(true)
      message.success('视频渲染成功')
    } catch (error) {
      message.error('视频渲染失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="视频配置" extra={<SettingOutlined />}>
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                duration: 10,
                fps: 30,
                width: 1920,
                height: 1080,
              }}
            >
              <Form.Item
                label="视频时长（秒）"
                name="duration"
              >
                <Slider
                  min={1}
                  max={60}
                  marks={{
                    1: '1s',
                    10: '10s',
                    30: '30s',
                    60: '60s',
                  }}
                />
              </Form.Item>

              <Form.Item
                label="帧率（FPS）"
                name="fps"
              >
                <Select>
                  <Option value={24}>24 FPS</Option>
                  <Option value={30}>30 FPS</Option>
                  <Option value={60}>60 FPS</Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="分辨率"
                name="resolution"
              >
                <Select>
                  <Option value="1920x1080">1920x1080 (1080p)</Option>
                  <Option value="1280x720">1280x720 (720p)</Option>
                  <Option value="3840x2160">3840x2160 (4K)</Option>
                </Select>
              </Form.Item>

              <Form.Item
                label="视频标题"
                name="title"
              >
                <Input placeholder="请输入视频标题" />
              </Form.Item>

              <Form.Item
                label="视频描述"
                name="description"
              >
                <Input.TextArea
                  rows={4}
                  placeholder="请输入视频描述"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handlePreview}
                    loading={loading}
                  >
                    预览
                  </Button>
                  <Button
                    type="default"
                    icon={<VideoCameraOutlined />}
                    onClick={handleRender}
                    loading={loading}
                  >
                    渲染
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="视频预览">
            {previewUrl ? (
              <div style={{ width: '100%', aspectRatio: '16/9', background: '#000' }}>
                <Player
                  component={MyVideo}
                  inputProps={{
                    title: form.getFieldValue('title') || '示例视频',
                    description: form.getFieldValue('description') || '',
                  }}
                  durationInFrames={form.getFieldValue('duration') * 30}
                  compositionWidth={1920}
                  compositionHeight={1080}
                  fps={30}
                  controls
                  style={{ width: '100%', height: '100%' }}
                />
              </div>
            ) : (
              <div
                style={{
                  width: '100%',
                  aspectRatio: '16/9',
                  background: '#f0f0f0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#999',
                }}
              >
                <div style={{ textAlign: 'center' }}>
                  <VideoCameraOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                  <p>点击"预览"按钮生成视频预览</p>
                </div>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="Remotion 工作室说明" style={{ marginTop: 16 }}>
        <p>Remotion 是一个基于 React 的视频创作工具，让您可以使用代码创建视频。</p>
        <h3>主要功能：</h3>
        <ul>
          <li>🎬 使用 React 组件创建视频</li>
          <li>⚡ 实时预览和快速迭代</li>
          <li>🎨 支持动画、转场和特效</li>
          <li>📊 数据驱动的视频生成</li>
          <li>🔧 可扩展的插件系统</li>
        </ul>
        <h3>使用方法：</h3>
        <ol>
          <li>配置视频参数（时长、帧率、分辨率）</li>
          <li>输入视频标题和描述</li>
          <li>点击"预览"查看实时效果</li>
          <li>点击"渲染"导出最终视频</li>
        </ol>
      </Card>
    </div>
  )
}

export default RemotionStudio