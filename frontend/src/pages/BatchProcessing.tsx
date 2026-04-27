import React, { useState, useEffect } from 'react'
import { Card, Form, Button, Upload, Select, message, Space, Row, Col, Divider, List, Tag, Radio, Input, InputNumber, Switch, Drawer, Descriptions, Table, Progress, Alert } from 'antd'
import { RocketOutlined, PlayCircleOutlined, DownloadOutlined, EyeOutlined, CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'

const { Option } = Select
const { TextArea } = Input

interface TaskResult {
  index: number
  id: string
  name: string
  type: string
  status: 'success' | 'failed' | 'skipped'
  error?: string
  output_files?: string[]
  execution_time?: number
}

interface ProcessingResult {
  success: boolean
  template_name: string
  total_tasks: number
  completed_tasks: number
  success_count: number
  failed_count: number
  skipped_count: number
  final_video?: string
  task_results: TaskResult[]
  total_execution_time?: number
  task_times?: Record<string, number>
  error?: string
}

interface TemplateInfo {
  name: string
  description: string
  version: string
  character?: string
  theme?: string
  task_count?: number
  parameters?: Record<string, any>
}

interface TemplateDetail {
  name: string
  description: string
  version: string
  character?: string
  theme?: string
  tasks: any[]
  parameters?: Record<string, any>
}

interface BatchProcessingConfig {
  templateName?: string
  username?: string
  age?: number
  theme?: string
  character?: string
  sub_character?: string
  tts_text?: string
  inputType: 'upload' | 'path'
  userImages: File[]
  userImagesPaths?: string
}

const BatchProcessing: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [results, setResults] = useState<ProcessingResult[]>([])
  const [userImages, setUserImages] = useState<File[]>([])
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateDetail | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [resultDetailVisible, setResultDetailVisible] = useState(false)
  const [selectedResult, setSelectedResult] = useState<ProcessingResult | null>(null)

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    setLoadingTemplates(true)
    try {
      const response = await fetch('/api/batch/templates', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data?.templates) {
        setTemplates(data.data.templates)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('获取模板列表失败')
    } finally {
      setLoadingTemplates(false)
    }
  }

  const fetchTemplateDetail = async (templateName: string) => {
    try {
      const response = await fetch(`/api/batch/template/${templateName}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data?.template) {
        setSelectedTemplate(data.data.template)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('获取模板详情失败')
    }
  }

  const handleTemplateChange = (templateName: string) => {
    if (templateName) {
      fetchTemplateDetail(templateName)
    } else {
      setSelectedTemplate(null)
    }
  }

  const handleFileChange = (info: any) => {
    const newFiles = info.fileList.map((file: any) => file.originFileObj).filter(Boolean)
    setUserImages(newFiles)
    form.setFieldsValue({ userImages: newFiles })
  }

  const handleProcess = async (values: BatchProcessingConfig) => {
    if (!values.templateName) {
      message.warning('请选择处理模板')
      return
    }

    if (values.inputType === 'upload' && userImages.length === 0) {
      message.warning('请上传用户图片')
      return
    }

    if (values.inputType === 'path' && (!values.userImagesPaths || !values.userImagesPaths.trim())) {
      message.warning('请输入用户图片路径列表')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('template_name', values.templateName)
      formData.append('username', values.username || '')
      formData.append('age', String(values.age || 6))
      formData.append('theme', values.theme || '生日快乐')
      formData.append('character', values.character || '奥特曼')
      formData.append('sub_character', values.sub_character || '')
      formData.append('tts_text', values.tts_text || '')

      if (values.inputType === 'upload') {
        userImages.forEach((file, index) => {
          formData.append(`user_images`, file)
        })
      } else {
        formData.append('user_images_paths', values.userImagesPaths || '')
      }

      const response = await fetch('/api/batch/execute', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        const result: ProcessingResult = {
          success: data.data?.success || true,
          template_name: data.data?.template_name || values.templateName,
          total_tasks: data.data?.total_tasks || 0,
          completed_tasks: data.data?.completed_tasks || 0,
          success_count: data.data?.success_count || 0,
          failed_count: data.data?.failed_count || 0,
          skipped_count: data.data?.skipped_count || 0,
          final_video: data.data?.final_video,
          task_results: data.data?.task_results || [],
          total_execution_time: data.data?.total_execution_time,
          task_times: data.data?.task_times,
          error: data.data?.error
        }
        setResults([result])
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

  const handleViewResultDetail = (result: ProcessingResult) => {
    setSelectedResult(result)
    setResultDetailVisible(true)
  }

  const renderParameterFormItem = (paramName: string, paramValue: any) => {
    const label = paramName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

    if (typeof paramValue === 'boolean') {
      return (
        <Form.Item
          key={paramName}
          name={paramName}
          label={label}
          valuePropName="checked"
          initialValue={paramValue}
        >
          <Switch />
        </Form.Item>
      )
    } else if (typeof paramValue === 'number') {
      return (
        <Form.Item
          key={paramName}
          name={paramName}
          label={label}
          initialValue={paramValue}
        >
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      )
    } else if (typeof paramValue === 'string') {
      if (paramValue.length > 100) {
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={paramValue}
          >
            <TextArea rows={4} />
          </Form.Item>
        )
      } else {
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={paramValue}
          >
            <Input />
          </Form.Item>
        )
      }
    }

    return null
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
            username: '',
            age: 6,
            theme: '生日快乐',
            character: '奥特曼',
            sub_character: '',
            tts_text: '',
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 输入配置</Divider>
              <Form.Item
                name="templateName"
                label="处理模板"
                rules={[{ required: true, message: '请选择处理模板' }]}
              >
                <Select
                  placeholder="请选择处理模板"
                  loading={loadingTemplates}
                  onChange={handleTemplateChange}
                  showSearch
                  optionFilterProp="children"
                >
                  {templates.map((template) => (
                    <Option key={template.name} value={template.name}>
                      {template.name} - {template.description}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              {selectedTemplate && (
                <>
                  <Form.Item
                    name="username"
                    label="用户名"
                  >
                    <Input placeholder="请输入用户名" />
                  </Form.Item>

                  <Form.Item
                    name="age"
                    label="年龄"
                  >
                    <InputNumber min={1} max={100} style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item
                    name="theme"
                    label="主题"
                  >
                    <Input placeholder="请输入主题" />
                  </Form.Item>

                  <Form.Item
                    name="character"
                    label="角色"
                  >
                    <Input placeholder="请输入角色" />
                  </Form.Item>

                  <Form.Item
                    name="sub_character"
                    label="二级角色"
                  >
                    <Input placeholder="请输入二级角色" />
                  </Form.Item>

                  <Form.Item
                    name="tts_text"
                    label="TTS文本"
                  >
                    <TextArea rows={4} placeholder="请输入TTS文本内容" />
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
                          name="userImages"
                          label="用户图片"
                          valuePropName="fileList"
                          getValueFromEvent={(e) => {
                            handleFileChange(e)
                            return e?.fileList
                          }}
                        >
                          <Upload.Dragger
                            accept="image/*"
                            multiple
                            maxCount={6}
                            beforeUpload={() => false}
                          >
                            <p className="ant-upload-drag-icon">
                              <RocketOutlined />
                            </p>
                            <p className="ant-upload-text">点击或拖拽多个图片到此处</p>
                            <p className="ant-upload-hint">支持批量处理多个图片文件（最多6张）</p>
                          </Upload.Dragger>
                        </Form.Item>
                      ) : (
                        <Form.Item
                          name="userImagesPaths"
                          label="用户图片路径列表"
                          rules={[{ required: true, message: '请输入用户图片路径列表' }]}
                          extra="每行一个路径，最多6张图片"
                        >
                          <TextArea
                            rows={6}
                            placeholder="输入图片文件路径，每行一个路径&#10;例如：&#10;/path/to/image1.jpg&#10;/path/to/image2.jpg"
                          />
                        </Form.Item>
                      )
                    }}
                  </Form.Item>
                </>
              )}

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<RocketOutlined />}
                  loading={loading}
                  block
                  disabled={!selectedTemplate}
                >
                  开始处理
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">📊 处理结果</Divider>
              {results.length > 0 ? (
                results.map((result, index) => (
                  <Card
                    key={index}
                    size="small"
                    style={{ marginBottom: 16 }}
                    title={
                      <Space>
                        <Tag color={result.success ? 'success' : 'error'}>
                          {result.success ? '成功' : '失败'}
                        </Tag>
                        <span>{result.template_name}</span>
                      </Space>
                    }
                    extra={
                      <Space>
                        {result.final_video && (
                          <>
                            <Button
                              type="link"
                              size="small"
                              icon={<DownloadOutlined />}
                              href={result.final_video}
                              download
                            >
                              下载
                            </Button>
                            <Button
                              type="link"
                              size="small"
                              icon={<PlayCircleOutlined />}
                              onClick={() => window.open(result.final_video, '_blank')}
                            >
                              预览
                            </Button>
                          </>
                        )}
                        <Button
                          type="link"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handleViewResultDetail(result)}
                        >
                          详情
                        </Button>
                      </Space>
                    }
                  >
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="总任务数">{result.total_tasks}</Descriptions.Item>
                      <Descriptions.Item label="已完成">{result.completed_tasks}</Descriptions.Item>
                      <Descriptions.Item label="成功">
                        <Tag color="success">{result.success_count}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="失败">
                        <Tag color="error">{result.failed_count}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="跳过">
                        <Tag color="warning">{result.skipped_count}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="总耗时">
                        {result.total_execution_time ? `${result.total_execution_time.toFixed(2)}秒` : '-'}
                      </Descriptions.Item>
                    </Descriptions>

                    {result.total_tasks > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <Progress
                          percent={Math.round((result.completed_tasks / result.total_tasks) * 100)}
                          status={result.failed_count > 0 ? 'exception' : 'active'}
                          size="small"
                        />
                      </div>
                    )}

                    {result.error && (
                      <Alert
                        message="执行错误"
                        description={result.error}
                        type="error"
                        showIcon
                        style={{ marginTop: 12 }}
                      />
                    )}
                  </Card>
                ))
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

              {selectedTemplate && (
                <>
                  <Divider orientation="left">📋 模板信息</Divider>
                  <Card size="small">
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="名称">{selectedTemplate.name}</Descriptions.Item>
                      <Descriptions.Item label="描述">{selectedTemplate.description}</Descriptions.Item>
                      <Descriptions.Item label="版本">{selectedTemplate.version}</Descriptions.Item>
                      <Descriptions.Item label="角色">{selectedTemplate.character || '-'}</Descriptions.Item>
                      <Descriptions.Item label="主题">{selectedTemplate.theme || '-'}</Descriptions.Item>
                      <Descriptions.Item label="任务数">{selectedTemplate.tasks?.length || 0}</Descriptions.Item>
                    </Descriptions>
                    <Button
                      type="link"
                      icon={<EyeOutlined />}
                      onClick={() => setDrawerVisible(true)}
                      style={{ marginTop: 8 }}
                    >
                      查看详细信息
                    </Button>
                  </Card>
                </>
              )}
            </Col>
          </Row>
        </Form>

        <Drawer
          title="模板详细信息"
          placement="right"
          width={600}
          open={drawerVisible}
          onClose={() => setDrawerVisible(false)}
        >
          {selectedTemplate && (
            <Descriptions column={1} bordered>
              <Descriptions.Item label="名称">{selectedTemplate.name}</Descriptions.Item>
              <Descriptions.Item label="描述">{selectedTemplate.description}</Descriptions.Item>
              <Descriptions.Item label="版本">{selectedTemplate.version}</Descriptions.Item>
              <Descriptions.Item label="角色">{selectedTemplate.character || '-'}</Descriptions.Item>
              <Descriptions.Item label="主题">{selectedTemplate.theme || '-'}</Descriptions.Item>
              <Descriptions.Item label="任务数">{selectedTemplate.tasks?.length || 0}</Descriptions.Item>
              <Descriptions.Item label="任务列表">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {JSON.stringify(selectedTemplate.tasks, null, 2)}
                </pre>
              </Descriptions.Item>
              <Descriptions.Item label="参数">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {JSON.stringify(selectedTemplate.parameters, null, 2)}
                </pre>
              </Descriptions.Item>
            </Descriptions>
          )}
        </Drawer>

        <Drawer
          title="任务执行详情"
          placement="right"
          width={800}
          open={resultDetailVisible}
          onClose={() => setResultDetailVisible(false)}
        >
          {selectedResult && (
            <>
              <Descriptions column={2} bordered style={{ marginBottom: 16 }}>
                <Descriptions.Item label="模板名称" span={2}>{selectedResult.template_name}</Descriptions.Item>
                <Descriptions.Item label="总任务数">{selectedResult.total_tasks}</Descriptions.Item>
                <Descriptions.Item label="已完成">{selectedResult.completed_tasks}</Descriptions.Item>
                <Descriptions.Item label="成功">
                  <Tag color="success" icon={<CheckCircleOutlined />}>{selectedResult.success_count}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="失败">
                  <Tag color="error" icon={<CloseCircleOutlined />}>{selectedResult.failed_count}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="跳过">
                  <Tag color="warning" icon={<MinusCircleOutlined />}>{selectedResult.skipped_count}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="总耗时">
                  {selectedResult.total_execution_time ? (
                    <Tag color="blue" icon={<ClockCircleOutlined />}>
                      {selectedResult.total_execution_time.toFixed(2)}秒
                    </Tag>
                  ) : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="最终视频" span={2}>
                  {selectedResult.final_video ? (
                    <Space>
                      <Button
                        type="link"
                        size="small"
                        icon={<DownloadOutlined />}
                        href={selectedResult.final_video}
                        download
                      >
                        下载
                      </Button>
                      <Button
                        type="link"
                        size="small"
                        icon={<PlayCircleOutlined />}
                        onClick={() => window.open(selectedResult.final_video, '_blank')}
                      >
                        预览
                      </Button>
                    </Space>
                  ) : '-'}
                </Descriptions.Item>
              </Descriptions>

              {selectedResult.error && (
                <Alert
                  message="执行错误"
                  description={selectedResult.error}
                  type="error"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              <Table
                dataSource={selectedResult.task_results}
                rowKey="id"
                pagination={false}
                size="small"
                columns={[
                  {
                    title: '序号',
                    dataIndex: 'index',
                    width: 60,
                    align: 'center',
                  },
                  {
                    title: '任务名称',
                    dataIndex: 'name',
                    width: 120,
                  },
                  {
                    title: '任务类型',
                    dataIndex: 'type',
                    width: 100,
                  },
                  {
                    title: '状态',
                    dataIndex: 'status',
                    width: 80,
                    render: (status: string) => {
                      if (status === 'success') {
                        return <Tag color="success" icon={<CheckCircleOutlined />}>成功</Tag>
                      } else if (status === 'failed') {
                        return <Tag color="error" icon={<CloseCircleOutlined />}>失败</Tag>
                      } else {
                        return <Tag color="warning" icon={<MinusCircleOutlined />}>跳过</Tag>
                      }
                    },
                  },
                  {
                    title: '输出文件',
                    dataIndex: 'output_files',
                    width: 200,
                    render: (files: string[]) => {
                      if (!files || files.length === 0) {
                        return '-'
                      }
                      return (
                        <div style={{ fontSize: 12 }}>
                          {files.map((file, idx) => (
                            <div key={idx} style={{ marginBottom: 4 }}>
                              <Button
                                type="link"
                                size="small"
                                style={{ padding: 0, height: 'auto' }}
                                onClick={() => window.open(file, '_blank')}
                              >
                                {file.split('/').pop()}
                              </Button>
                            </div>
                          ))}
                        </div>
                      )
                    },
                  },
                  {
                    title: '耗时',
                    dataIndex: 'execution_time',
                    width: 80,
                    render: (time?: number) => {
                      return time ? `${time.toFixed(2)}秒` : '-'
                    },
                  },
                  {
                    title: '备注',
                    dataIndex: 'error',
                    width: 150,
                    render: (error?: string) => {
                      if (error) {
                        return <span style={{ color: '#f44336', fontSize: 12 }}>{error}</span>
                      }
                      return '-'
                    },
                  },
                ]}
              />
            </>
          )}
        </Drawer>
      </Card>
    </div>
  )
}

export default BatchProcessing