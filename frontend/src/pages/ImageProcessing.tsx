import React, { useState } from 'react'
import { Card, Form, Button, Upload, message, Space, Row, Col, Divider, Radio, Slider, Select, Input } from 'antd'
import { PictureOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons'

const { Option } = Select

interface ImageProcessingConfig {
  inputType: 'upload' | 'path'
  imageFile: any[]
  imagePath?: string
  backgroundImageFile?: any[]
  backgroundImagePath?: string
  operation: 'remove-bg' | 'blend'
  blendMode?: string
  opacity?: number
}

const ImageProcessing: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const handleProcess = async (values: ImageProcessingConfig) => {
    if (values.inputType === 'upload' && (!values.imageFile || values.imageFile.length === 0)) {
      message.warning('请先上传图片')
      return
    }

    if (values.inputType === 'path' && !values.imagePath) {
      message.warning('请输入图片路径')
      return
    }

    if (values.operation === 'blend' && values.inputType === 'upload' && (!values.backgroundImageFile || values.backgroundImageFile.length === 0)) {
      message.warning('请上传背景图片')
      return
    }

    if (values.operation === 'blend' && values.inputType === 'path' && !values.backgroundImagePath) {
      message.warning('请输入背景图片路径')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('input_type', values.inputType)

      if (values.inputType === 'upload') {
        const imageFile = values.imageFile[0]?.originFileObj
        if (imageFile) {
          formData.append('image', imageFile)
        }
      } else {
        if (values.imagePath) {
          formData.append('image_path', values.imagePath)
        }
      }

      let apiUrl = ''
      if (values.operation === 'remove-bg') {
        apiUrl = '/api/image/remove_background'
      } else if (values.operation === 'blend') {
        apiUrl = '/api/image/blend'
        if (values.inputType === 'upload') {
          const baseImageFile = values.backgroundImageFile[0]?.originFileObj
          if (baseImageFile) {
            formData.append('base_image', baseImageFile)
          }
          const overlayImageFile = values.imageFile[0]?.originFileObj
          if (overlayImageFile) {
            formData.append('overlay_image', overlayImageFile)
          }
        } else {
          if (values.backgroundImagePath) {
            formData.append('base_image_path', values.backgroundImagePath)
          }
          if (values.imagePath) {
            formData.append('overlay_image_path', values.imagePath)
          }
        }
        formData.append('position_x', '85')
        formData.append('position_y', '90')
        formData.append('scale', (values.opacity || 1.0).toString())
        formData.append('width', '425')
        formData.append('height', '615')
        formData.append('remove_bg', 'true')
      }

      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setPreviewUrl(data.data?.output_path || data.output_path)
        message.success('图片处理成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('图片处理失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="🖼️ 图像处理" extra={<PictureOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleProcess}
          initialValues={{
            inputType: 'upload',
            operation: 'remove-bg',
            blendMode: 'normal',
            opacity: 1.0,
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 上传图片</Divider>
              <Form.Item
                name="inputType"
                label="输入类型"
              >
                <Radio.Group>
                  <Radio value="upload">上传文件</Radio>
                  <Radio value="path">路径方式</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item
                name="operation"
                label="操作类型"
              >
                <Radio.Group>
                  <Radio value="remove-bg">去背景</Radio>
                  <Radio value="blend">图片混合</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.inputType !== currentValues.inputType}>
                {({ getFieldValue }) => {
                  const inputType = getFieldValue('inputType')

                  return inputType === 'upload' ? (
                    <>
                      <Form.Item
                        name="imageFile"
                        label="主图片"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                        rules={[{ required: true, message: '请上传图片' }]}
                      >
                        <Upload.Dragger
                          accept="image/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <PictureOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽图片到此处</p>
                        </Upload.Dragger>
                      </Form.Item>
                    </>
                  ) : (
                    <>
                      <Form.Item
                        name="imagePath"
                        label="主图片路径"
                        rules={[{ required: true, message: '请输入图片路径' }]}
                      >
                        <Input placeholder="输入图片文件的URL或本地路径" />
                      </Form.Item>
                    </>
                  )
                }}
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.operation !== currentValues.operation || prevValues.inputType !== currentValues.inputType}>
                {({ getFieldValue }) => {
                  const operation = getFieldValue('operation')
                  const inputType = getFieldValue('inputType')

                  return operation === 'blend' ? (
                    <>
                      {inputType === 'upload' ? (
                        <Form.Item
                          name="backgroundImageFile"
                          label="背景图片"
                          valuePropName="fileList"
                          getValueFromEvent={(e) => e && e.fileList}
                          rules={[{ required: true, message: '请上传背景图片' }]}
                        >
                          <Upload.Dragger
                            accept="image/*"
                            maxCount={1}
                            beforeUpload={() => false}
                          >
                            <p className="ant-upload-drag-icon">
                              <PictureOutlined />
                            </p>
                            <p className="ant-upload-text">点击或拖拽背景图片到此处</p>
                          </Upload.Dragger>
                        </Form.Item>
                      ) : (
                        <Form.Item
                          name="backgroundImagePath"
                          label="背景图片路径"
                          rules={[{ required: true, message: '请输入背景图片路径' }]}
                        >
                          <Input placeholder="输入背景图片文件的URL或本地路径" />
                        </Form.Item>
                      )}

                      <Form.Item
                        name="blendMode"
                        label="混合模式"
                      >
                        <Select>
                          <Option value="normal">正常</Option>
                          <Option value="multiply">正片叠底</Option>
                          <Option value="screen">滤色</Option>
                          <Option value="overlay">叠加</Option>
                          <Option value="darken">变暗</Option>
                          <Option value="lighten">变亮</Option>
                        </Select>
                      </Form.Item>

                      <Form.Item
                        name="opacity"
                        label="不透明度"
                      >
                        <Slider
                          min={0}
                          max={1}
                          step={0.1}
                          marks={{
                            0: '0',
                            0.5: '0.5',
                            1: '1',
                          }}
                        />
                      </Form.Item>
                    </>
                  ) : null
                }}
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PictureOutlined />}
                  loading={loading}
                  block
                >
                  处理图片
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">👁️ 预览结果</Divider>
              {previewUrl ? (
                <Card size="small">
                  <img
                    src={previewUrl}
                    alt="处理结果"
                    style={{ width: '100%', borderRadius: 8 }}
                  />
                  <Space style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
                    <Button
                      type="primary"
                      icon={<DownloadOutlined />}
                      href={previewUrl}
                      download
                    >
                      下载图片
                    </Button>
                    <Button
                      icon={<EyeOutlined />}
                      onClick={() => window.open(previewUrl, '_blank')}
                    >
                      查看原图
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
                    <PictureOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>处理后的图片将在这里显示</p>
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

export default ImageProcessing