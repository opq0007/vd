import React, { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Upload, List, Tag, Drawer, Descriptions, Card, Row, Col, Select, Radio, Divider } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOutlined, DownloadOutlined, EyeOutlined, CodeOutlined, UnorderedListOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd'

const { Option } = Select

interface Template {
  name: string
  description: string
  version: string
  tasks: any[]
  template_dir?: string
  created_at?: string
  updated_at?: string
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

interface Resource {
  name: string
  path: string
  size: number
}

interface Task {
  type: string
  params: Record<string, any>
}

const TemplateManager: React.FC = () => {
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null)
  const [viewingTemplate, setViewingTemplate] = useState<TemplateInfo | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [resourcesDrawerVisible, setResourcesDrawerVisible] = useState(false)
  const [selectedTemplateForResources, setSelectedTemplateForResources] = useState<string>('')
  const [resources, setResources] = useState<Resource[]>([])
  const [resourcesLoading, setResourcesLoading] = useState(false)
  const [tasksEditMode, setTasksEditMode] = useState<'json' | 'list'>('json')
  const [tasksList, setTasksList] = useState<Task[]>([])
  const [editingTaskIndex, setEditingTaskIndex] = useState<number | null>(null)
  const [taskModalVisible, setTaskModalVisible] = useState(false)
  const [taskForm] = Form.useForm()
  const [form] = Form.useForm()

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/templates', {
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
      setLoading(false)
    }
  }

  const fetchTemplateDetail = async (templateName: string) => {
    try {
      const response = await fetch(`/api/templates/${templateName}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data) {
        setViewingTemplate(data.data)
        setDrawerVisible(true)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('获取模板详情失败')
    }
  }

  const fetchResources = async (templateName: string) => {
    setResourcesLoading(true)
    try {
      const response = await fetch(`/api/templates/${templateName}/resources`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data?.resources) {
        setResources(data.data.resources)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('获取资源文件列表失败')
    } finally {
      setResourcesLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingTemplate(null)
    form.resetFields()
    setTasksList([])
    setTasksEditMode('json')
    setModalVisible(true)
  }

  const handleEdit = async (templateName: string) => {
    try {
      const response = await fetch(`/api/templates/${templateName}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data) {
        setEditingTemplate(data.data)
        const formData = { ...data.data }
        if (formData.tasks && Array.isArray(formData.tasks)) {
          formData.tasks = JSON.stringify(formData.tasks, null, 2)
          setTasksList(formData.tasks)
        } else {
          setTasksList([])
        }
        form.setFieldsValue(formData)
        setTasksEditMode('json')
        setModalVisible(true)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('获取模板详情失败')
    }
  }

  const handleDelete = (templateName: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除模板 "${templateName}" 吗？`,
      onOk: async () => {
        try {
          const response = await fetch(`/api/templates/${templateName}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
            },
          })
          const data = await response.json()
          if (data.success) {
            message.success('删除成功')
            fetchTemplates()
          } else {
            message.error(data.error || data.message)
          }
        } catch (error) {
          message.error('删除失败')
        }
      },
    })
  }

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields()
      const templateName = values.name

      const formData = { ...values }

      if (tasksEditMode === 'list') {
        formData.tasks = tasksList
      } else if (formData.tasks && typeof formData.tasks === 'string') {
        try {
          formData.tasks = JSON.parse(formData.tasks)
        } catch (error) {
          message.error('任务配置格式错误，请检查 JSON 格式')
          return
        }
      }

      const response = await fetch(`/api/templates/${templateName}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      const data = await response.json()
      if (data.success) {
        message.success(editingTemplate ? '更新成功' : '创建成功')
        setModalVisible(false)
        form.resetFields()
        taskForm.resetFields()
        setTasksList([])
        fetchTemplates()
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleTasksEditModeChange = (mode: 'json' | 'list') => {
    if (mode === 'list') {
      const tasksValue = form.getFieldValue('tasks')
      if (tasksValue && typeof tasksValue === 'string') {
        try {
          const parsedTasks = JSON.parse(tasksValue)
          if (Array.isArray(parsedTasks)) {
            setTasksList(parsedTasks)
          } else {
            setTasksList([])
          }
        } catch (error) {
          message.error('JSON 格式错误，无法转换为列表模式')
          return
        }
      }
    } else {
      const jsonValue = JSON.stringify(tasksList, null, 2)
      form.setFieldsValue({ tasks: jsonValue })
    }
    setTasksEditMode(mode)
  }

  const handleAddTask = () => {
    setEditingTaskIndex(null)
    taskForm.resetFields()
    taskForm.setFieldsValue({ type: 'tts', params: '{}' })
    setTaskModalVisible(true)
  }

  const handleEditTask = (index: number) => {
    setEditingTaskIndex(index)
    const task = tasksList[index]
    taskForm.setFieldsValue({
      type: task.type,
      params: JSON.stringify(task.params, null, 2)
    })
    setTaskModalVisible(true)
  }

  const handleDeleteTask = (index: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个任务吗？',
      onOk: () => {
        const newTasksList = [...tasksList]
        newTasksList.splice(index, 1)
        setTasksList(newTasksList)
        message.success('删除成功')
      },
    })
  }

  const handleTaskModalOk = () => {
    taskForm.validateFields().then(values => {
      let params: Record<string, any>
      try {
        params = JSON.parse(values.params)
      } catch (error) {
        message.error('参数格式错误，请检查 JSON 格式')
        return
      }

      const newTask: Task = {
        type: values.type,
        params: params
      }

      if (editingTaskIndex !== null) {
        const newTasksList = [...tasksList]
        newTasksList[editingTaskIndex] = newTask
        setTasksList(newTasksList)
        message.success('更新成功')
      } else {
        setTasksList([...tasksList, newTask])
        message.success('添加成功')
      }

      setTaskModalVisible(false)
      taskForm.resetFields()
    })
  }

  const handleViewResources = (templateName: string) => {
    setSelectedTemplateForResources(templateName)
    setResourcesDrawerVisible(true)
    fetchResources(templateName)
  }

  const handleUploadResource = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/templates/${selectedTemplateForResources}/resources`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
        body: formData,
      })

      const data = await response.json()
      if (data.success) {
        message.success('上传成功')
        fetchResources(selectedTemplateForResources)
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('上传失败')
    }

    return false
  }

  const handleDownloadResource = (resourceName: string) => {
    window.open(`/api/templates/${selectedTemplateForResources}/resources/${resourceName}`, '_blank')
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
    },
    {
      title: '角色',
      dataIndex: 'character',
      key: 'character',
      width: 100,
    },
    {
      title: '主题',
      dataIndex: 'theme',
      key: 'theme',
      width: 100,
    },
    {
      title: '任务数',
      dataIndex: 'task_count',
      key: 'task_count',
      width: 80,
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      render: (_: any, record: TemplateInfo) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => fetchTemplateDetail(record.name)}
          >
            查看
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FolderOutlined />}
            onClick={() => handleViewResources(record.name)}
          >
            资源
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record.name)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.name)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleAdd}
        >
          新建模板
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={templates}
        rowKey="name"
        loading={loading}
      />

      <Modal
        title={editingTemplate ? '编辑模板' : '新建模板'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
          taskForm.resetFields()
          setTasksList([])
          setTasksEditMode('json')
        }}
        width={800}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            label="模板名称"
            name="name"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" disabled={!!editingTemplate} />
          </Form.Item>
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入模板描述' }]}
          >
            <Input.TextArea
              rows={4}
              placeholder="请输入模板描述"
            />
          </Form.Item>
          <Form.Item
            label="版本"
            name="version"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="例如：1.0.0" />
          </Form.Item>

          <Divider orientation="left">任务配置</Divider>

          <Form.Item label="编辑模式">
            <Radio.Group
              value={tasksEditMode}
              onChange={(e) => handleTasksEditModeChange(e.target.value)}
            >
              <Radio.Button value="json"><CodeOutlined /> JSON 编辑</Radio.Button>
              <Radio.Button value="list"><UnorderedListOutlined /> 列表编辑</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {tasksEditMode === 'json' ? (
            <Form.Item
              name="tasks"
              rules={[
                { required: true, message: '请输入任务配置' },
                {
                  validator: (_, value) => {
                    if (!value) return Promise.resolve()
                    try {
                      JSON.parse(value)
                      return Promise.resolve()
                    } catch (error) {
                      return Promise.reject(new Error('任务配置格式错误，请检查 JSON 格式'))
                    }
                  }
                }
              ]}
            >
              <Input.TextArea
                rows={12}
                placeholder='请输入任务配置（JSON格式）&#10;例如：&#10;[&#10;  {&#10;    "type": "tts",&#10;    "params": {&#10;      "text": "生日快乐",&#10;      "feat_id": "default"&#10;    }&#10;  },&#10;  {&#10;    "type": "subtitle",&#10;    "params": {&#10;      "model_name": "small",&#10;      "device": "cpu"&#10;    }&#10;  }&#10;]'
              />
            </Form.Item>
          ) : (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddTask}
                >
                  添加任务
                </Button>
              </div>

              {tasksList.length === 0 ? (
                <Card size="small">
                  <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                    暂无任务，点击上方按钮添加
                  </div>
                </Card>
              ) : (
                <List
                  dataSource={tasksList}
                  renderItem={(task: Task, index: number) => (
                    <List.Item
                      actions={[
                        <Button
                          type="link"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => handleEditTask(index)}
                        >
                          编辑
                        </Button>,
                        <Button
                          type="link"
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => handleDeleteTask(index)}
                        >
                          删除
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color="blue">{task.type}</Tag>
                            <span>任务 {index + 1}</span>
                          </Space>
                        }
                        description={
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12 }}>
                            {JSON.stringify(task.params, null, 2)}
                          </pre>
                        }
                      />
                    </List.Item>
                  )}
                />
              )}
            </div>
          )}
        </Form>
      </Modal>

      <Modal
        title={editingTaskIndex !== null ? '编辑任务' : '添加任务'}
        open={taskModalVisible}
        onOk={handleTaskModalOk}
        onCancel={() => {
          setTaskModalVisible(false)
          taskForm.resetFields()
        }}
        width={600}
      >
        <Form form={taskForm} layout="vertical">
          <Form.Item
            label="任务类型"
            name="type"
            rules={[{ required: true, message: '请选择任务类型' }]}
          >
            <Select placeholder="请选择任务类型">
              <Option value="tts">TTS 语音合成</Option>
              <Option value="subtitle">字幕生成</Option>
              <Option value="video_edit">视频编辑</Option>
              <Option value="image_process">图像处理</Option>
              <Option value="transition">视频转场</Option>
              <Option value="merge">视频合并</Option>
              <Option value="email">邮件发送</Option>
              <Option value="http">HTTP 集成</Option>
              <Option value="custom">自定义任务</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="任务参数（JSON格式）"
            name="params"
            rules={[
              { required: true, message: '请输入任务参数' },
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve()
                  try {
                    JSON.parse(value)
                    return Promise.resolve()
                  } catch (error) {
                    return Promise.reject(new Error('参数格式错误，请检查 JSON 格式'))
                  }
                }
              }
            ]}
          >
            <Input.TextArea
              rows={10}
              placeholder='请输入任务参数（JSON格式）&#10;例如：&#10;{&#10;  "text": "生日快乐",&#10;  "feat_id": "default",&#10;  "cfg_value": 2.0&#10;}'
            />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="模板详情"
        placement="right"
        width={600}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      >
        {viewingTemplate && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="名称">{viewingTemplate.name}</Descriptions.Item>
            <Descriptions.Item label="描述">{viewingTemplate.description}</Descriptions.Item>
            <Descriptions.Item label="版本">{viewingTemplate.version}</Descriptions.Item>
            <Descriptions.Item label="角色">{viewingTemplate.character || '-'}</Descriptions.Item>
            <Descriptions.Item label="主题">{viewingTemplate.theme || '-'}</Descriptions.Item>
            <Descriptions.Item label="任务数">{viewingTemplate.task_count || 0}</Descriptions.Item>
            <Descriptions.Item label="参数">
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {JSON.stringify(viewingTemplate.parameters, null, 2)}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <Drawer
        title={`资源文件 - ${selectedTemplateForResources}`}
        placement="right"
        width={600}
        open={resourcesDrawerVisible}
        onClose={() => setResourcesDrawerVisible(false)}
      >
        <Card
          style={{ marginBottom: 16 }}
          type="inner"
          title="上传资源"
        >
          <Upload
            beforeUpload={handleUploadResource}
            showUploadList={false}
          >
            <Button icon={<PlusOutlined />}>上传文件</Button>
          </Upload>
        </Card>

        <List
          loading={resourcesLoading}
          dataSource={resources}
          renderItem={(resource: Resource) => (
            <List.Item
              actions={[
                <Button
                  type="link"
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownloadResource(resource.name)}
                >
                  下载
                </Button>,
              ]}
            >
              <List.Item.Meta
                avatar={<FolderOutlined />}
                title={resource.name}
                description={`${(resource.size / 1024).toFixed(2)} KB`}
              />
            </List.Item>
          )}
        />
      </Drawer>
    </div>
  )
}

export default TemplateManager