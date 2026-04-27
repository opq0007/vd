import React, { useState, useEffect } from 'react'
import { Card, Form, Button, Upload, Select, Slider, message, Space, Row, Col, Divider, Radio, Input, InputNumber, Switch } from 'antd'
import { SwapOutlined, PlayCircleOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactPlayer from 'react-player'

const { Option } = Select

interface VideoTransitionConfig {
  inputType: 'upload' | 'path'
  videoFile1: any[]
  videoFile2: any[]
  videoPath1?: string
  videoPath2?: string
  transitionType: string
  duration: number
}

interface TransitionParam {
  type: string
  default: any
  min?: number
  max?: number
  step?: number
  options?: string[]
  description?: string
}

interface TransitionInfo {
  name: string
  class: string
  params: Record<string, TransitionParam>
  category: string
}

const VideoTransition: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [transitions, setTransitions] = useState<Record<string, TransitionInfo>>({})
  const [transitionParams, setTransitionParams] = useState<Record<string, TransitionParam>>({})
  const [loadingTransitions, setLoadingTransitions] = useState(false)

  // 获取转场效果列表
  useEffect(() => {
    fetchTransitions()
  }, [])

  const fetchTransitions = async () => {
    try {
      setLoadingTransitions(true)
      const response = await fetch('/api/transition/list', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data?.transitions) {
        setTransitions(data.data.transitions)
        // 默认选择第一个转场效果
        const firstTransition = Object.keys(data.data.transitions)[0]
        if (firstTransition) {
          form.setFieldsValue({ transitionType: firstTransition })
          fetchTransitionParams(firstTransition)
        }
      } else {
        message.error('获取转场效果列表失败')
      }
    } catch (error) {
      console.error('获取转场效果列表失败:', error)
      message.error('获取转场效果列表失败')
    } finally {
      setLoadingTransitions(false)
    }
  }

  const fetchTransitionParams = async (transitionName: string) => {
    try {
      const response = await fetch(`/api/transition/params/${transitionName}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || 'opq#key'}`,
        },
      })
      const data = await response.json()
      if (data.success && data.data?.params) {
        setTransitionParams(data.data.params)
      } else {
        message.error('获取转场参数配置失败')
      }
    } catch (error) {
      console.error('获取转场参数配置失败:', error)
      message.error('获取转场参数配置失败')
    }
  }

  const handleTransitionTypeChange = (value: string) => {
    fetchTransitionParams(value)
  }

  const handleTransition = async (values: VideoTransitionConfig) => {
    if (values.inputType === 'upload' && (!values.videoFile1 || values.videoFile1.length === 0 || !values.videoFile2 || values.videoFile2.length === 0)) {
      message.warning('请上传两个视频文件')
      return
    }

    if (values.inputType === 'path' && (!values.videoPath1 || !values.videoPath2)) {
      message.warning('请输入两个视频路径')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('input_type', values.inputType)

      if (values.inputType === 'upload') {
        const videoFile1 = values.videoFile1[0]?.originFileObj
        const videoFile2 = values.videoFile2[0]?.originFileObj

        if (videoFile1) {
          formData.append('video1', videoFile1)
        }
        if (videoFile2) {
          formData.append('video2', videoFile2)
        }
      } else {
        if (values.videoPath1) {
          formData.append('video1_path', values.videoPath1)
        }
        if (values.videoPath2) {
          formData.append('video2_path', values.videoPath2)
        }
      }
      formData.append('transition_name', values.transitionType)

      // 添加转场参数
      Object.keys(transitionParams).forEach(paramName => {
        const param = transitionParams[paramName]
        const value = values[paramName] !== undefined ? values[paramName] : param.default
        formData.append(paramName, String(value))
      })

      const response = await fetch('/api/transition/apply', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setPreviewUrl(data.data?.output_path || data.output_path)
        message.success('视频转场成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('视频转场失败')
    } finally {
      setLoading(false)
    }
  }

  // 渲染参数表单项
  const renderParamFormItem = (paramName: string, param: TransitionParam) => {
    const label = param.description || paramName

    switch (param.type) {
      case 'choice':
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={param.default}
          >
            <Select>
              {param.options?.map(option => (
                <Option key={option} value={option}>{option}</Option>
              ))}
            </Select>
          </Form.Item>
        )

      case 'int':
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={param.default}
          >
            <InputNumber
              min={param.min}
              max={param.max}
              style={{ width: '100%' }}
            />
          </Form.Item>
        )

      case 'float':
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={param.default}
          >
            <InputNumber
              min={param.min}
              max={param.max}
              step={param.step || 0.1}
              style={{ width: '100%' }}
            />
          </Form.Item>
        )

      case 'boolean':
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            valuePropName="checked"
            initialValue={param.default}
          >
            <Switch />
          </Form.Item>
        )

      case 'string':
        return (
          <Form.Item
            key={paramName}
            name={paramName}
            label={label}
            initialValue={param.default}
          >
            <Input />
          </Form.Item>
        )

      default:
        return null
    }
  }

  return (
    <div>
      <Card title="🎬 视频转场" extra={<SwapOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleTransition}
          initialValues={{
            inputType: 'upload',
            transitionType: 'crossfade',
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
                        name="videoFile1"
                        label="第一个视频"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                        rules={[{ required: true, message: '请上传第一个视频' }]}
                      >
                        <Upload.Dragger
                          accept="video/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <SwapOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽第一个视频到此处</p>
                        </Upload.Dragger>
                      </Form.Item>

                      <Form.Item
                        name="videoFile2"
                        label="第二个视频"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                        rules={[{ required: true, message: '请上传第二个视频' }]}
                      >
                        <Upload.Dragger
                          accept="video/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <SwapOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽第二个视频到此处</p>
                        </Upload.Dragger>
                      </Form.Item>
                    </>
                  ) : (
                    <>
                      <Form.Item
                        name="videoPath1"
                        label="第一个视频路径"
                        rules={[{ required: true, message: '请输入第一个视频路径' }]}
                      >
                        <Input placeholder="输入第一个视频文件的URL或本地路径" />
                      </Form.Item>

                      <Form.Item
                        name="videoPath2"
                        label="第二个视频路径"
                        rules={[{ required: true, message: '请输入第二个视频路径' }]}
                      >
                        <Input placeholder="输入第二个视频文件的URL或本地路径" />
                      </Form.Item>
                    </>
                  )
                }}
              </Form.Item>

              <Form.Item
                name="transitionType"
                label="转场类型"
              >
                <Select
                  loading={loadingTransitions}
                  onChange={handleTransitionTypeChange}
                >
                  {Object.entries(transitions).map(([key, transition]) => (
                    <Option key={key} value={key}>
                      {transition.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Divider orientation="left">⚙️ 转场参数</Divider>
              {Object.entries(transitionParams).map(([paramName, param]) =>
                renderParamFormItem(paramName, param)
              )}

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SwapOutlined />}
                  loading={loading}
                  block
                >
                  应用转场
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
                    <SwapOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>转场后的视频将在这里显示</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </Form>
      </Card>
    </div>
  )
}

export default VideoTransition