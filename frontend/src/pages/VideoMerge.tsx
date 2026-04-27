import React, { useState } from 'react'
import { Card, Form, Button, Upload, Select, Slider, message, Space, Row, Col, Divider, List, Radio, Input } from 'antd'
import { LinkOutlined, PlayCircleOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons'
import ReactPlayer from 'react-player'

const { Option } = Select
const { TextArea } = Input

interface VideoMergeConfig {
  inputType: 'upload' | 'path'
  videoFiles: File[]
  videoPaths?: string
  mergeMode: 'concat' | 'overlay'
  outputFormat: string
  quality: number
}

const VideoMerge: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [videoFiles, setVideoFiles] = useState<File[]>([])

  const handleFileChange = (info: any) => {
    const newFiles = info.fileList.map((file: any) => file.originFileObj).filter(Boolean)
    setVideoFiles(newFiles)
    form.setFieldsValue({ videoFiles: newFiles })
  }

  const handleRemoveFile = (index: number) => {
    const newFiles = videoFiles.filter((_, i) => i !== index)
    setVideoFiles(newFiles)
    form.setFieldsValue({ videoFiles: newFiles })
  }

  const handleMerge = async (values: VideoMergeConfig) => {
    if (values.inputType === 'upload' && videoFiles.length < 2) {
      message.warning('请至少上传两个视频文件')
      return
    }

    if (values.inputType === 'path' && (!values.videoPaths || !values.videoPaths.trim())) {
      message.warning('请输入视频路径列表')
      return
    }

    if (values.inputType === 'path' && values.videoPaths) {
      const pathCount = values.videoPaths.split('\n').filter(p => p.trim()).length
      if (pathCount < 2) {
        message.warning('请至少输入两个视频路径')
        return
      }
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('input_type', values.inputType)

      if (values.inputType === 'upload') {
        const videoPaths = videoFiles.map(f => f.name).join('\n')
        formData.append('video_paths', videoPaths)
      } else {
        formData.append('video_paths', values.videoPaths || '')
      }

      formData.append('out_basename', 'merged_video')
      formData.append('delete_intermediate_videos', 'true')

      const response = await fetch('/api/video_merge/merge', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setPreviewUrl(data.data?.output_path || data.output_path)
        message.success('视频合并成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('视频合并失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="🔗 视频合并" extra={<LinkOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleMerge}
          initialValues={{
            inputType: 'upload',
            mergeMode: 'concat',
            outputFormat: 'mp4',
            quality: 23,
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 上传视频</Divider>
              <Form.Item
                name="inputType"
                label="输入类型"
              >
                <Radio.Group>
                  <Radio value="upload">上传文件</Radio>
                  <Radio value="path">路径方式</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.inputType !== currentValues.inputType}>
                {({ getFieldValue }) => {
                  const inputType = getFieldValue('inputType')

                  return inputType === 'upload' ? (
                    <>
                      <Form.Item
                        name="videoFiles"
                        label="视频文件（至少2个）"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => {
                          handleFileChange(e)
                          return e?.fileList
                        }}
                      >
                        <Upload.Dragger
                          accept="video/*"
                          multiple
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <LinkOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽多个视频到此处</p>
                          <p className="ant-upload-hint">支持同时上传多个视频文件</p>
                        </Upload.Dragger>
                      </Form.Item>

                      {videoFiles.length > 0 && (
                        <Card size="small" title="已上传的视频" style={{ marginBottom: 16 }}>
                          <List
                            dataSource={videoFiles}
                            renderItem={(file, index) => (
                              <List.Item
                                actions={[
                                  <Button
                                    type="text"
                                    danger
                                    icon={<DeleteOutlined />}
                                    onClick={() => handleRemoveFile(index)}
                                  >
                                    删除
                                  </Button>,
                                ]}
                              >
                                <List.Item.Meta
                                  title={`视频 ${index + 1}`}
                                  description={`${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`}
                                />
                              </List.Item>
                            )}
                          />
                        </Card>
                      )}
                    </>
                  ) : (
                    <>
                      <Form.Item
                        name="videoPaths"
                        label="视频文件路径列表"
                        rules={[{ required: true, message: '请输入视频路径列表' }]}
                        extra="每行一个路径，至少需要两个视频"
                      >
                        <TextArea
                          rows={6}
                          placeholder="输入视频文件路径，每行一个路径&#10;例如：&#10;/path/to/video1.mp4&#10;/path/to/video2.mp4"
                        />
                      </Form.Item>
                    </>
                  )
                }}
              </Form.Item>

              <Form.Item
                name="mergeMode"
                label="合并模式"
              >
                <Select>
                  <Option value="concat">顺序拼接</Option>
                  <Option value="overlay">叠加</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="outputFormat"
                label="输出格式"
              >
                <Select>
                  <Option value="mp4">MP4</Option>
                  <Option value="avi">AVI</Option>
                  <Option value="mov">MOV</Option>
                  <Option value="webm">WebM</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="quality"
                label="视频质量（CRF值）"
                tooltip="CRF值越低，质量越高，文件越大"
              >
                <Slider
                  min={18}
                  max={28}
                  step={1}
                  marks={{
                    18: '18 (高质量)',
                    23: '23 (默认)',
                    28: '28 (低质量)',
                  }}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<LinkOutlined />}
                  loading={loading}
                  block
                  disabled={videoFiles.length < 2}
                >
                  合并视频
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">👁️ 预览结果</Divider>
              {previewUrl ? (
                <Card size="small">
                  <ReactPlayer
                    url={previewUrl}
                    controls
                    width="100%"
                    height={300}
                  />
                  <Space style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      href={previewUrl}
                      download
                    >
                      下载视频
                    </Button>
                    <Button
                      icon={<PlayCircleOutlined />}
                      onClick={() => window.open(previewUrl, '_blank')}
                    >
                      新窗口播放
                    </Button>
                  </Space>
                </Card>
              ) : (
                <Card size="small">
                  <div
                    style={{
                      textAlign: 'center',
                      padding: 40,
                      color: '#999',
                    }}
                  >
                    <LinkOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>合并后的视频将在这里显示</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📋 合并说明</Divider>
        <Card size="small">
          <h4>合并模式说明：</h4>
          <ul>
            <li><strong>顺序拼接</strong>：将多个视频按顺序连接成一个视频</li>
            <li><strong>叠加</strong>：将多个视频叠加在一起（需要视频尺寸相同）</li>
          </ul>
          <h4>质量说明：</h4>
          <ul>
            <li><strong>CRF 18</strong>：高质量，文件较大</li>
            <li><strong>CRF 23</strong>：默认质量，平衡质量和大小</li>
            <li><strong>CRF 28</strong>：低质量，文件较小</li>
          </ul>
        </Card>
      </Card>
    </div>
  )
}

export default VideoMerge