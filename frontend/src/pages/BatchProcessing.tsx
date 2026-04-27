import React, { useState } from 'react'
import { Card, Form, Button, Upload, Select, message, Space, Row, Col, Divider, List, Tag, Radio, Input } from 'antd'
import { RocketOutlined, PlayCircleOutlined, DownloadOutlined } from '@ant-design/icons'

const { Option } = Select
const { TextArea } = Input

interface BatchProcessingConfig {
  templateId?: string
  inputType: 'upload' | 'path'
  videoFiles: File[]
  videoPaths?: string
  processingMode: 'parallel' | 'sequential'
}

const BatchProcessing: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any[]>([])
  const [videoFiles, setVideoFiles] = useState<File[]>([])

  const handleFileChange = (info: any) => {
    const newFiles = info.fileList.map((file: any) => file.originFileObj).filter(Boolean)
    setVideoFiles(newFiles)
    form.setFieldsValue({ videoFiles: newFiles })
  }

  const handleProcess = async (values: BatchProcessingConfig) => {
    if (!values.templateId) {
      message.warning('请选择处理模板')
      return
    }

    if (values.inputType === 'upload' && videoFiles.length === 0) {
      message.warning('请上传视频文件')
      return
    }

    if (values.inputType === 'path' && (!values.videoPaths || !values.videoPaths.trim())) {
      message.warning('请输入视频路径列表')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('template_name', values.templateId)
      formData.append('username', 'user')
      formData.append('age', '6')
      formData.append('theme', '生日快乐')
      formData.append('character', '奥特曼')

      if (values.inputType === 'upload') {
        const imagePaths = videoFiles.map(f => f.name).join('\n')
        formData.append('user_images_paths', imagePaths)
      } else {
        formData.append('user_images_paths', values.videoPaths || '')
      }

      const response = await fetch('/api/batch/execute', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setResults([{
          success: true,
          message: '处理成功',
          output_path: data.data?.output_path || data.output_path
        }])
        message.success('批量处理成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('批量处理失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="🚀 综合处理" extra={<RocketOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleProcess}
          initialValues={{
            inputType: 'upload',
            processingMode: 'parallel',
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 上传视频</Divider>
              <Form.Item
                name="templateId"
                label="处理模板"
                rules={[{ required: true, message: '请选择处理模板' }]}
              >
                <Select placeholder="请选择处理模板">
                  <Option value="template1">模板1 - 基础处理</Option>
                  <Option value="template2">模板2 - 高级处理</Option>
                  <Option value="template3">模板3 - 专业处理</Option>
                </Select>
              </Form.Item>

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
                    <Form.Item
                      name="videoFiles"
                      label="视频文件"
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
                          <RocketOutlined />
                        </p>
                        <p className="ant-upload-text">点击或拖拽多个视频到此处</p>
                        <p className="ant-upload-hint">支持批量处理多个视频文件</p>
                      </Upload.Dragger>
                    </Form.Item>
                  ) : (
                    <Form.Item
                      name="videoPaths"
                      label="视频文件路径列表"
                      rules={[{ required: true, message: '请输入视频路径列表' }]}
                      extra="每行一个路径"
                    >
                      <TextArea
                        rows={6}
                        placeholder="输入视频文件路径，每行一个路径&#10;例如：&#10;/path/to/video1.mp4&#10;/path/to/video2.mp4"
                      />
                    </Form.Item>
                  )
                }}
              </Form.Item>

              <Form.Item
                name="processingMode"
                label="处理模式"
              >
                <Select>
                  <Option value="parallel">并行处理</Option>
                  <Option value="sequential">顺序处理</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<RocketOutlined />}
                  loading={loading}
                  block
                  disabled={videoFiles.length === 0}
                >
                  开始处理
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">📊 处理结果</Divider>
              {results.length > 0 ? (
                <List
                  dataSource={results}
                  renderItem={(item: any, index) => (
                    <List.Item
                      actions={[
                        <Button
                          type="link"
                          icon={<DownloadOutlined />}
                          href={item.output_path}
                          download
                        >
                          下载
                        </Button>,
                        <Button
                          type="link"
                          icon={<PlayCircleOutlined />}
                          onClick={() => window.open(item.output_path, '_blank')}
                        >
                          预览
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={`视频 ${index + 1}`}
                        description={
                          <Space>
                            <Tag color={item.success ? 'success' : 'error'}>
                              {item.success ? '成功' : '失败'}
                            </Tag>
                            <span>{item.message}</span>
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Card size="small">
                  <div
                    style={{
                      textAlign: 'center',
                      padding: 40,
                      color: '#999',
                    }}
                  >
                    <RocketOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>处理结果将在这里显示</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📋 处理说明</Divider>
        <Card size="small">
          <h4>处理模式说明：</h4>
          <ul>
            <li><strong>并行处理</strong>：同时处理多个视频，速度更快但占用更多资源</li>
            <li><strong>顺序处理</strong>：依次处理每个视频，速度较慢但资源占用少</li>
          </ul>
          <h4>模板说明：</h4>
          <ul>
            <li><strong>模板1</strong>：基础处理 - 包含字幕生成、音频调整等基础功能</li>
            <li><strong>模板2</strong>：高级处理 - 包含转场、特效等高级功能</li>
            <li><strong>模板3</strong>：专业处理 - 包含所有功能，适合专业用途</li>
          </ul>
        </Card>
      </Card>
    </div>
  )
}

export default BatchProcessing