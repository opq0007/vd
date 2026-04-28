import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Button,
  message,
  Space,
  Row,
  Col,
  Divider,
  Select,
  Upload,
  Modal,
  Table,
  Tabs,
  Tag,
  Alert,
  InputNumber,
  Descriptions,
} from 'antd'
import {
  PictureOutlined,
  CloudUploadOutlined,
  SettingOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
  FolderOpenOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons'
import ReactPlayer from 'react-player'

const { TextArea } = Input
const { Option } = Select
const { TabPane } = Tabs

interface ComfyUIConfig {
  server_url: string
  auth_token?: string
}

interface WorkflowTemplate {
  filename: string
  path: string
  size: number
}

interface WorkflowParamsInfo {
  parameters: string[]
  example: Record<string, any>
  count: number
}

interface OutputImage {
  url: string
  filename: string
  subfolder: string
  type: string
}

interface OutputFile {
  filename: string
  subfolder: string
  type: string
}

interface ExecutionResult {
  success: boolean
  output_images?: OutputImage[]
  output_audio?: OutputFile[]
  output_videos?: OutputFile[]
  output_files?: OutputFile[]
  error?: string
}

interface UploadedFile {
  name: string
  path: string
  size: number
  type: string
}

const ComfyUIIntegration: React.FC = () => {
  const [configForm] = Form.useForm()
  const [executionForm] = Form.useForm()

  const [config, setConfig] = useState<ComfyUIConfig>({
    server_url: 'http://127.0.0.1:8188',
    auth_token: '',
  })
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('')
  const [workflowParams, setWorkflowParams] = useState<WorkflowParamsInfo | null>(null)
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<WorkflowTemplate | null>(null)
  const [workflowJson, setWorkflowJson] = useState('')
  const [loading, setLoading] = useState(false)
  const [paramsJsonVisible, setParamsJsonVisible] = useState(false)

  useEffect(() => {
    const savedConfig = localStorage.getItem('comfyui_config')
    if (savedConfig) {
      const parsedConfig = JSON.parse(savedConfig)
      setConfig(parsedConfig)
      configForm.setFieldsValue(parsedConfig)
    }
    
    fetchWorkflows()
    fetchUploadedFiles()
  }, [configForm])

  const saveConfig = (values: ComfyUIConfig) => {
    setConfig(values)
    localStorage.setItem('comfyui_config', JSON.stringify(values))
    message.success('配置已保存')
  }

  const testConnection = async () => {
    setConnectionStatus('testing')
    try {
      const response = await fetch('/api/comfyui/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const data = await response.json()

      if (data.success) {
        setConnectionStatus('success')
        message.success('连接成功')
      } else {
        setConnectionStatus('error')
        message.error(data.error || '连接失败')
      }
    } catch (error) {
      setConnectionStatus('error')
      message.error('连接失败')
    }
  }

  const fetchWorkflows = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/comfyui/workflows')
      const data = await response.json()

      if (data.success) {
        setWorkflows(data.data?.workflows || [])
      } else {
        message.error(data.error || '获取工作流列表失败')
      }
    } catch (error) {
      message.error('获取工作流列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleWorkflowUpload = async (file: File) => {
    try {
      const fileContent = await file.text()
      const workflowJson = JSON.parse(fileContent)
      
      const formData = new FormData()
      formData.append('workflow_name', file.name)
      formData.append('workflow_json', JSON.stringify(workflowJson))
      formData.append('overwrite', 'false')

      const response = await fetch('/api/comfyui/workflow/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        message.success('工作流上传成功')
        fetchWorkflows()
      } else {
        message.error(data.error || '工作流上传失败')
      }
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('工作流文件格式错误，请确保是有效的 JSON 文件')
      } else {
        message.error('工作流上传失败')
      }
    }

    return false
  }

  const deleteWorkflow = async (workflowName: string) => {
    try {
      const response = await fetch(`/api/comfyui/workflow/${workflowName}`, {
        method: 'DELETE',
      })

      const data = await response.json()

      if (data.success) {
        message.success('工作流删除成功')
        fetchWorkflows()
      } else {
        message.error(data.error || '工作流删除失败')
      }
    } catch (error) {
      message.error('工作流删除失败')
    }
  }

  const editWorkflow = (workflow: WorkflowTemplate) => {
    setEditingWorkflow(workflow)
    setEditModalVisible(true)
    setWorkflowJson('')

    fetch(`/api/comfyui/workflow/${workflow.filename}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          const workflowData = data.data?.workflow || {}
          setWorkflowJson(JSON.stringify(workflowData, null, 2))
        } else {
          message.error(data.error || '获取工作流详情失败')
        }
      })
      .catch(() => {
        message.error('获取工作流详情失败')
      })
  }

  const saveEditedWorkflow = async () => {
    if (!editingWorkflow) return

    try {
      const formData = new FormData()
      formData.append('workflow_name', editingWorkflow.filename)
      formData.append('workflow_json', workflowJson)
      formData.append('overwrite', 'true')

      const response = await fetch('/api/comfyui/workflow/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        message.success('工作流保存成功')
        setEditModalVisible(false)
        fetchWorkflows()
      } else {
        message.error(data.error || '工作流保存失败')
      }
    } catch (error) {
      message.error('工作流保存失败')
    }
  }

  const loadWorkflowParams = async (workflowName: string) => {
    setSelectedWorkflow(workflowName)
    setLoading(true)
    try {
      const response = await fetch(`/api/comfyui/workflow/${workflowName}/params`)
      const data = await response.json()

      if (data.success) {
        setWorkflowParams(data.data)
        executionForm.resetFields()
        
        if (data.data?.example) {
          executionForm.setFieldsValue(data.data.example)
        }
      } else {
        message.error(data.error || '获取工作流参数失败')
        setWorkflowParams(null)
      }
    } catch (error) {
      message.error('获取工作流参数失败')
      setWorkflowParams(null)
    } finally {
      setLoading(false)
    }
  }

  const executeWorkflow = async (values: any) => {
    if (!selectedWorkflow) {
      message.warning('请先选择工作流')
      return
    }

    setLoading(true)
    setExecutionResult(null)

    try {
      const formData = new FormData()
      formData.append('workflow_name', selectedWorkflow)
      formData.append('params', JSON.stringify(values))
      
      if (config.server_url) {
        formData.append('server_url', config.server_url)
      }
      if (config.auth_token) {
        formData.append('auth_token', config.auth_token)
      }

      const response = await fetch('/api/comfyui/execute_from_template', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setExecutionResult({
          success: true,
          output_images: data.data?.output_images || [],
          output_audio: data.data?.output_audio || [],
          output_videos: data.data?.output_videos || [],
          output_files: data.data?.output_files || [],
        })
        message.success('工作流执行成功')
      } else {
        setExecutionResult({
          success: false,
          error: data.error || data.message,
        })
        message.error(data.error || '工作流执行失败')
      }
    } catch (error) {
      setExecutionResult({
        success: false,
        error: error instanceof Error ? error.message : '未知错误',
      })
      message.error('工作流执行失败')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/comfyui/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        message.success('文件上传成功')
        fetchUploadedFiles()
      } else {
        message.error(data.error || '文件上传失败')
      }
    } catch (error) {
      message.error('文件上传失败')
    }

    return false
  }

  const fetchUploadedFiles = async () => {
    try {
      const response = await fetch('/api/comfyui/files')
      const data = await response.json()

      if (data.success) {
        setUploadedFiles(data.data?.files || [])
      }
    } catch (error) {
      message.error('获取文件列表失败')
    }
  }

  const renderParameterFormItem = (paramName: string, exampleValue: any) => {
    const paramLower = paramName.toLowerCase()
    
    if (paramLower.includes('seed') || paramLower.includes('width') || 
        paramLower.includes('height') || paramLower.includes('steps') || 
        paramLower.includes('cfg')) {
      return (
        <Form.Item
          key={paramName}
          name={paramName}
          label={paramName}
          initialValue={exampleValue}
        >
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      )
    }
    
    return (
      <Form.Item
        key={paramName}
        name={paramName}
        label={paramName}
        initialValue={exampleValue}
      >
        <Input />
      </Form.Item>
    )
  }

  const workflowColumns = [
    {
      title: '名称',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => `${(size / 1024).toFixed(2)} KB`,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: WorkflowTemplate) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => editWorkflow(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => deleteWorkflow(record.filename)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  const fileColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => `${(size / 1024).toFixed(2)} KB`,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
    },
  ]

  return (
    <div>
      <Card title="🎨 ComfyUI 集成" extra={<PictureOutlined />}>
        <Tabs defaultActiveKey="config">
          <TabPane tab="配置" key="config">
            <Card size="small" style={{ marginBottom: 16 }}>
              <Form
                form={configForm}
                layout="vertical"
                onFinish={saveConfig}
                initialValues={config}
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="server_url"
                      label="服务器地址"
                      rules={[{ required: true, message: '请输入服务器地址' }]}
                    >
                      <Input placeholder="http://127.0.0.1:8188" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="auth_token" label="认证令牌（可选）">
                      <Input.Password placeholder="输入认证令牌" />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" icon={<SettingOutlined />}>
                      保存配置
                    </Button>
                    <Button
                      icon={<ThunderboltOutlined />}
                      onClick={testConnection}
                      loading={connectionStatus === 'testing'}
                    >
                      测试连接
                    </Button>
                  </Space>
                </Form.Item>

                {connectionStatus === 'success' && (
                  <Alert
                    message="连接成功"
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                  />
                )}
                {connectionStatus === 'error' && (
                  <Alert
                    message="连接失败"
                    type="error"
                    showIcon
                    icon={<CloseCircleOutlined />}
                  />
                )}
              </Form>
            </Card>

            <Descriptions title="配置说明" bordered size="small">
              <Descriptions.Item label="服务器地址">
                ComfyUI 服务器的地址，默认为 http://127.0.0.1:8188
              </Descriptions.Item>
              <Descriptions.Item label="认证令牌">
                如果 ComfyUI 服务器启用了认证，请输入令牌
              </Descriptions.Item>
              <Descriptions.Item label="测试连接">
                点击测试连接按钮验证配置是否正确
              </Descriptions.Item>
            </Descriptions>
          </TabPane>

          <TabPane tab="工作流" key="workflows">
            <Card
              size="small"
              title="工作流管理"
              extra={
                <Space>
                  <Upload
                    accept=".json"
                    beforeUpload={handleWorkflowUpload}
                    showUploadList={false}
                  >
                    <Button icon={<CloudUploadOutlined />}>上传工作流</Button>
                  </Upload>
                  <Button icon={<FileTextOutlined />} onClick={fetchWorkflows}>
                    刷新列表
                  </Button>
                </Space>
              }
            >
              <Table
                columns={workflowColumns}
                dataSource={workflows}
                rowKey="filename"
                loading={loading}
                pagination={false}
              />
            </Card>
          </TabPane>

          <TabPane tab="执行" key="execution">
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="工作流执行">
                  <Form
                    form={executionForm}
                    layout="vertical"
                    onFinish={executeWorkflow}
                  >
                    <Form.Item
                      label="选择工作流"
                      rules={[{ required: true, message: '请选择工作流' }]}
                    >
                      <Select
                        placeholder="选择要执行的工作流"
                        onChange={loadWorkflowParams}
                        value={selectedWorkflow}
                      >
                        {workflows.map((workflow) => (
                          <Option key={workflow.filename} value={workflow.filename}>
                            {workflow.filename}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>

                    {workflowParams && workflowParams.count > 0 && (
                      <>
                        <Divider orientation="left">
                          参数配置 ({workflowParams.count} 个参数)
                          <Button
                            type="link"
                            size="small"
                            onClick={() => setParamsJsonVisible(true)}
                            style={{ marginLeft: 8 }}
                          >
                            查看JSON格式
                          </Button>
                        </Divider>
                        <Alert
                          message="参数说明"
                          description={
                            <div>
                              <p>此工作流需要以下参数，已自动填充示例值：</p>
                              <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                                {workflowParams.parameters.map((param) => (
                                  <li key={param}>
                                    <strong>{param}</strong>: {JSON.stringify(workflowParams.example[param])}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          }
                          type="info"
                          showIcon
                          style={{ marginBottom: 16 }}
                        />
                        {workflowParams.parameters.map((paramName) => 
                          renderParameterFormItem(paramName, workflowParams.example[paramName])
                        )}
                      </>
                    )}

                    {workflowParams && workflowParams.count === 0 && (
                      <Alert
                        message="无需参数"
                        description="此工作流不需要任何参数配置"
                        type="success"
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}

                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<ThunderboltOutlined />}
                        loading={loading}
                        block
                      >
                        执行工作流
                      </Button>
                    </Form.Item>
                  </Form>
                </Card>
              </Col>

              <Col span={12}>
                {executionResult && (
                  <Card
                    size="small"
                    title="执行结果"
                    extra={
                      executionResult.success ? (
                        <Tag color="success" icon={<CheckCircleOutlined />}>
                          成功
                        </Tag>
                      ) : (
                        <Tag color="error" icon={<CloseCircleOutlined />}>
                          失败
                        </Tag>
                      )
                    }
                  >
                    {executionResult.success ? (
                      <>
                        {executionResult.output_images &&
                          executionResult.output_images.length > 0 && (
                            <>
                              <Divider orientation="left">输出图像</Divider>
                              <Space direction="vertical" style={{ width: '100%' }}>
                                {executionResult.output_images.map((image, index) => {
                                  let proxyUrl = `/api/comfyui/proxy/view?filename=${encodeURIComponent(image.filename)}&subfolder=${encodeURIComponent(image.subfolder)}&type=${encodeURIComponent(image.type)}`
                                  if (config.server_url) {
                                    proxyUrl += `&server_url=${encodeURIComponent(config.server_url)}`
                                  }
                                  if (config.auth_token) {
                                    proxyUrl += `&auth_token=${encodeURIComponent(config.auth_token)}`
                                  }
                                  return (
                                    <div key={index} style={{ marginBottom: 16 }}>
                                      <img
                                        src={proxyUrl}
                                        alt={`Output ${index}`}
                                        style={{
                                          width: '100%',
                                          borderRadius: 8,
                                          marginBottom: 8,
                                        }}
                                      />
                                      <div style={{ fontSize: 12, color: '#999' }}>
                                        文件名: {image.filename}
                                      </div>
                                    </div>
                                  )
                                })}
                              </Space>
                            </>
                          )}

                        {executionResult.output_audio &&
                          executionResult.output_audio.length > 0 && (
                            <>
                              <Divider orientation="left">输出音频</Divider>
                              <Space direction="vertical" style={{ width: '100%' }}>
                                {executionResult.output_audio.map((audio, index) => (
                                  <ReactPlayer
                                    key={index}
                                    url={`/api/file/download?file_path=${audio}`}
                                    controls
                                    width="100%"
                                    height={50}
                                  />
                                ))}
                              </Space>
                            </>
                          )}

                        {executionResult.output_videos &&
                          executionResult.output_videos.length > 0 && (
                            <>
                              <Divider orientation="left">输出视频</Divider>
                              <Space direction="vertical" style={{ width: '100%' }}>
                                {executionResult.output_videos.map((video, index) => (
                                  <ReactPlayer
                                    key={index}
                                    url={`/api/file/download?file_path=${video}`}
                                    controls
                                    width="100%"
                                  />
                                ))}
                              </Space>
                            </>
                          )}
                      </>
                    ) : (
                      <Alert
                        message="执行失败"
                        description={executionResult.error}
                        type="error"
                        showIcon
                      />
                    )}
                  </Card>
                )}
              </Col>
            </Row>
          </TabPane>

          <TabPane tab="文件" key="files">
            <Card
              size="small"
              title="文件管理"
              extra={
                <Space>
                  <Upload
                    beforeUpload={handleFileUpload}
                    showUploadList={false}
                  >
                    <Button icon={<CloudUploadOutlined />}>上传文件</Button>
                  </Upload>
                  <Button icon={<FolderOpenOutlined />} onClick={fetchUploadedFiles}>
                    刷新列表
                  </Button>
                </Space>
              }
            >
              <Table
                columns={fileColumns}
                dataSource={uploadedFiles}
                rowKey="name"
                loading={loading}
                pagination={false}
              />
            </Card>
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title={`编辑工作流: ${editingWorkflow?.filename}`}
        open={editModalVisible}
        onOk={saveEditedWorkflow}
        onCancel={() => setEditModalVisible(false)}
        width={800}
      >
        <TextArea
          value={workflowJson}
          onChange={(e) => setWorkflowJson(e.target.value)}
          rows={20}
          style={{ fontFamily: 'monospace' }}
        />
      </Modal>

      <Modal
        title="参数配置 (JSON格式)"
        open={paramsJsonVisible}
        onCancel={() => setParamsJsonVisible(false)}
        footer={[
          <Button key="close" onClick={() => setParamsJsonVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {workflowParams && (
          <div>
            <Alert
              message="参数说明"
              description="以下JSON格式展示了当前工作流所需的所有参数及其示例值，您可以直接复制使用或修改后提交。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <TextArea
              value={JSON.stringify(workflowParams.example, null, 2)}
              readOnly
              rows={20}
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ComfyUIIntegration