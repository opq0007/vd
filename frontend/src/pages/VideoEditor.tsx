import React, { useState, useEffect } from 'react'
import { Card, Form, Button, Upload, Select, Slider, message, Space, Row, Col, Divider, InputNumber, Radio, Input, ColorPicker, Switch, Collapse } from 'antd'
import { ScissorOutlined, PlayCircleOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactPlayer from 'react-player'
import { apiClient } from '../services/api'

const { Option } = Select
const { Panel } = Collapse

interface VideoEditorConfig {
  inputType: 'upload' | 'path'
  videoFile: any[]
  videoPath?: string
  audioFile?: any[]
  audioPath?: string
  // 基础编辑参数
  enableTrim?: boolean
  startTime?: number
  endTime?: number
  enableCrop?: boolean
  cropX?: number
  cropY?: number
  cropWidth?: number
  cropHeight?: number
  enableSpeed?: boolean
  speed?: number
  enableVolume?: boolean
  volume?: number
  // 花字参数
  enableFlower?: boolean
  flowerText?: string
  flowerFont?: string
  flowerSize?: number
  flowerColor?: string
  flowerColorMode?: '单色' | '渐变'
  flowerGradientType?: '水平渐变' | '垂直渐变' | '对角渐变'
  flowerColorStart?: string
  flowerColorEnd?: string
  flowerX?: number
  flowerY?: number
  flowerTimingType?: '时间戳范围' | '帧范围'
  flowerStartFrame?: number
  flowerEndFrame?: number
  flowerStartTime?: string
  flowerEndTime?: string
  flowerStrokeEnabled?: boolean
  flowerStrokeColor?: string
  flowerStrokeWidth?: number
  flowerAnimationEnabled?: boolean
  flowerAnimationType?: string
  flowerAnimationSpeed?: number
  flowerAnimationAmplitude?: number
  flowerAnimationDirection?: string
  // 插图参数
  enableImage?: boolean
  imagePath?: string
  imageX?: number
  imageY?: number
  imageWidth?: number
  imageHeight?: number
  imageTimingType?: '时间戳范围' | '帧范围'
  imageStartFrame?: number
  imageEndFrame?: number
  imageStartTime?: string
  imageEndTime?: string
  imageRemoveBg?: boolean
  // 插视频参数
  enableVideo?: boolean
  videoPathToInsert?: string
  videoX?: number
  videoY?: number
  videoWidth?: number
  videoHeight?: number
  videoTimingType?: '时间戳范围' | '帧范围'
  videoStartFrame?: number
  videoEndFrame?: number
  videoStartTime?: string
  videoEndTime?: string
  // 水印参数
  enableWatermark?: boolean
  watermarkText?: string
  watermarkFont?: string
  watermarkSize?: number
  watermarkColor?: string
  watermarkTimingType?: '时间戳范围' | '帧范围'
  watermarkStartFrame?: number
  watermarkEndFrame?: number
  watermarkStartTime?: string
  watermarkEndTime?: string
  watermarkStyle?: string
}

const VideoEditor: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [fonts, setFonts] = useState<string[]>([])

  useEffect(() => {
    fetchFonts()
  }, [])

  const fetchFonts = async () => {
    try {
      const response = await apiClient.get<{ fonts: string[] }>('/video_editor/fonts')
      if (response.success && response.data?.fonts) {
        setFonts(response.data.fonts)
      }
    } catch (error) {
      console.error('获取字体列表失败:', error)
      message.error('获取字体列表失败')
    }
  }

  const handleEdit = async (values: VideoEditorConfig) => {
    if (values.inputType === 'upload' && (!values.videoFile || values.videoFile.length === 0)) {
      message.warning('请先上传视频')
      return
    }

    if (values.inputType === 'path' && !values.videoPath) {
      message.warning('请输入视频路径')
      return
    }

    // 检查是否至少启用了一个功能
    const hasEnabledFeature =
      values.enableTrim ||
      values.enableCrop ||
      values.enableSpeed ||
      values.enableVolume ||
      values.enableFlower ||
      values.enableImage ||
      values.enableVideo ||
      values.enableWatermark

    if (!hasEnabledFeature) {
      message.warning('请至少启用一个编辑功能')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('input_type', values.inputType)

      // 处理视频和音频文件
      if (values.inputType === 'upload') {
        const videoFile = values.videoFile[0]?.originFileObj
        if (videoFile) {
          formData.append('video_file', videoFile)
        }
        if (values.audioFile && values.audioFile.length > 0) {
          const audioFile = values.audioFile[0]?.originFileObj
          if (audioFile) {
            formData.append('audio_file', audioFile)
          }
        }
      } else {
        if (values.videoPath) {
          formData.append('video_path', values.videoPath)
        }
        if (values.audioPath) {
          formData.append('audio_path', values.audioPath)
        }
      }

      // 花字参数
      if (values.enableFlower && values.flowerText) {
        formData.append('flower_text', values.flowerText)
        formData.append('flower_font', values.flowerFont || 'Microsoft YaHei')
        formData.append('flower_size', (values.flowerSize || 40).toString())
        formData.append('flower_color', values.flowerColor || '#FFFFFF')
        formData.append('flower_color_mode', values.flowerColorMode || '单色')
        formData.append('flower_gradient_type', values.flowerGradientType || '水平渐变')
        formData.append('flower_color_start', values.flowerColorStart || '#FF0000')
        formData.append('flower_color_end', values.flowerColorEnd || '#0000FF')
        formData.append('flower_x', (values.flowerX || 100).toString())
        formData.append('flower_y', (values.flowerY || 100).toString())
        formData.append('flower_timing_type', values.flowerTimingType || '时间戳范围')
        formData.append('flower_start_frame', (values.flowerStartFrame || 0).toString())
        formData.append('flower_end_frame', (values.flowerEndFrame || 100).toString())
        formData.append('flower_start_time', values.flowerStartTime || '00:00:00')
        formData.append('flower_end_time', values.flowerEndTime || '00:00:05')
        formData.append('flower_stroke_enabled', (values.flowerStrokeEnabled || false).toString())
        formData.append('flower_stroke_color', values.flowerStrokeColor || '#000000')
        formData.append('flower_stroke_width', (values.flowerStrokeWidth || 2).toString())
        formData.append('flower_animation_enabled', (values.flowerAnimationEnabled || false).toString())
        formData.append('flower_animation_type', values.flowerAnimationType || '无效果')
        formData.append('flower_animation_speed', (values.flowerAnimationSpeed || 1.0).toString())
        formData.append('flower_animation_amplitude', (values.flowerAnimationAmplitude || 20.0).toString())
        formData.append('flower_animation_direction', values.flowerAnimationDirection || 'left')
      }

      // 插图参数
      if (values.enableImage && values.imagePath) {
        formData.append('image_path', values.imagePath)
        formData.append('image_x', (values.imageX || 200).toString())
        formData.append('image_y', (values.imageY || 200).toString())
        formData.append('image_width', (values.imageWidth || 200).toString())
        formData.append('image_height', (values.imageHeight || 150).toString())
        formData.append('image_timing_type', values.imageTimingType || '时间戳范围')
        formData.append('image_start_frame', (values.imageStartFrame || 0).toString())
        formData.append('image_end_frame', (values.imageEndFrame || 100).toString())
        formData.append('image_start_time', values.imageStartTime || '00:00:00')
        formData.append('image_end_time', values.imageEndTime || '00:00:05')
        formData.append('image_remove_bg', (values.imageRemoveBg || true).toString())
      }

      // 插视频参数
      if (values.enableVideo && values.videoPathToInsert) {
        formData.append('video_path_to_insert', values.videoPathToInsert)
        formData.append('video_x', (values.videoX || 10).toString())
        formData.append('video_y', (values.videoY || 10).toString())
        formData.append('video_width', (values.videoWidth || 200).toString())
        formData.append('video_height', (values.videoHeight || 150).toString())
        formData.append('video_timing_type', values.videoTimingType || '时间戳范围')
        formData.append('video_start_frame', (values.videoStartFrame || 0).toString())
        formData.append('video_end_frame', (values.videoEndFrame || 999999).toString())
        formData.append('video_start_time', values.videoStartTime || '00:00:00')
        formData.append('video_end_time', values.videoEndTime || '99:59:59')
      }

      // 水印参数
      if (values.enableWatermark && values.watermarkText) {
        formData.append('watermark_text', values.watermarkText)
        formData.append('watermark_font', values.watermarkFont || '黑体.TTF')
        formData.append('watermark_size', (values.watermarkSize || 20).toString())
        formData.append('watermark_color', values.watermarkColor || '#FFFFFF')
        formData.append('watermark_timing_type', values.watermarkTimingType || '时间戳范围')
        formData.append('watermark_start_frame', (values.watermarkStartFrame || 0).toString())
        formData.append('watermark_end_frame', (values.watermarkEndFrame || 999999).toString())
        formData.append('watermark_start_time', values.watermarkStartTime || '00:00:00')
        formData.append('watermark_end_time', values.watermarkEndTime || '99:59:59')
        formData.append('watermark_style', values.watermarkStyle || '半透明浮动')
      }

      // 基础编辑参数（用于标记操作类型）
      if (values.enableTrim) {
        formData.append('flower_text', '剪辑')
        formData.append('flower_font', 'Microsoft YaHei')
        formData.append('flower_size', '40')
        formData.append('flower_color', '#FFFFFF')
        formData.append('flower_x', '100')
        formData.append('flower_y', '100')
        formData.append('flower_start_frame', Math.floor((values.startTime || 0) * 25).toString())
        formData.append('flower_end_frame', Math.floor((values.endTime || 10) * 25).toString())
      } else if (values.enableCrop) {
        formData.append('flower_text', '裁剪')
        formData.append('flower_x', (values.cropX || 0).toString())
        formData.append('flower_y', (values.cropY || 0).toString())
      } else if (values.enableSpeed) {
        formData.append('flower_text', '变速')
      } else if (values.enableVolume) {
        formData.append('flower_text', '音量')
        formData.append('audio_volume', (values.volume || 1.0).toString())
      }

      const response = await fetch('/api/video_editor/apply_effects', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setPreviewUrl(data.data?.video_output_path || data.data?.output_path)
        message.success('视频编辑成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('视频编辑失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="✂️ 视频编辑" extra={<ScissorOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleEdit}
          initialValues={{
            inputType: 'upload',
            // 基础编辑默认值
            enableTrim: false,
            startTime: 0,
            endTime: 10,
            enableCrop: false,
            cropX: 0,
            cropY: 0,
            enableSpeed: false,
            speed: 1.0,
            enableVolume: false,
            volume: 1.0,
            // 花字默认值
            enableFlower: false,
            flowerFont: 'Microsoft YaHei',
            flowerSize: 40,
            flowerColor: '#FFFFFF',
            flowerColorMode: '单色',
            flowerGradientType: '水平渐变',
            flowerColorStart: '#FF0000',
            flowerColorEnd: '#0000FF',
            flowerX: 100,
            flowerY: 100,
            flowerTimingType: '时间戳范围',
            flowerStartFrame: 0,
            flowerEndFrame: 100,
            flowerStartTime: '00:00:00',
            flowerEndTime: '00:00:05',
            flowerStrokeEnabled: false,
            flowerStrokeColor: '#000000',
            flowerStrokeWidth: 2,
            flowerAnimationEnabled: false,
            flowerAnimationType: '无效果',
            flowerAnimationSpeed: 1.0,
            flowerAnimationAmplitude: 20.0,
            flowerAnimationDirection: 'left',
            // 插图默认值
            enableImage: false,
            imageX: 200,
            imageY: 200,
            imageWidth: 200,
            imageHeight: 150,
            imageTimingType: '时间戳范围',
            imageStartFrame: 0,
            imageEndFrame: 100,
            imageStartTime: '00:00:00',
            imageEndTime: '00:00:05',
            imageRemoveBg: true,
            // 插视频默认值
            enableVideo: false,
            videoX: 10,
            videoY: 10,
            videoWidth: 200,
            videoHeight: 150,
            videoTimingType: '时间戳范围',
            videoStartFrame: 0,
            videoEndFrame: 999999,
            videoStartTime: '00:00:00',
            videoEndTime: '99:59:59',
            // 水印默认值
            enableWatermark: false,
            watermarkFont: '黑体.TTF',
            watermarkSize: 20,
            watermarkColor: '#FFFFFF',
            watermarkTimingType: '时间戳范围',
            watermarkStartFrame: 0,
            watermarkEndFrame: 999999,
            watermarkStartTime: '00:00:00',
            watermarkEndTime: '99:59:59',
            watermarkStyle: '半透明浮动',
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 输入设置</Divider>
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
                        name="videoFile"
                        label="视频文件"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                        rules={[{ required: true, message: '请上传视频' }]}
                      >
                        <Upload.Dragger
                          accept="video/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <ScissorOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽视频到此处</p>
                        </Upload.Dragger>
                      </Form.Item>

                      <Form.Item
                        name="audioFile"
                        label="音频文件（可选）"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                      >
                        <Upload.Dragger
                          accept="audio/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <ScissorOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽音频到此处</p>
                        </Upload.Dragger>
                      </Form.Item>
                    </>
                  ) : (
                    <>
                      <Form.Item
                        name="videoPath"
                        label="视频文件路径"
                        rules={[{ required: true, message: '请输入视频路径' }]}
                      >
                        <Input placeholder="输入视频文件的URL或本地路径" />
                      </Form.Item>

                      <Form.Item
                        name="audioPath"
                        label="音频文件路径（可选）"
                      >
                        <Input placeholder="输入音频文件的URL或本地路径" />
                      </Form.Item>
                    </>
                  )
                }}
              </Form.Item>

              <Divider orientation="left">🎨 编辑功能</Divider>
              <Collapse defaultActiveKey={['flower']} expandIconPosition="end">
                {/* 基础编辑功能 */}
                <Panel header="📏 基础编辑" key="basic">
                  <Form.Item
                    name="enableTrim"
                    label="启用裁剪"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableTrim !== currentValues.enableTrim}>
                    {({ getFieldValue }) => {
                      const enableTrim = getFieldValue('enableTrim')
                      return enableTrim ? (
                        <>
                          <Form.Item
                            name="startTime"
                            label="开始时间（秒）"
                          >
                            <Slider
                              min={0}
                              max={60}
                              step={0.1}
                              marks={{
                                0: '0s',
                                10: '10s',
                                30: '30s',
                                60: '60s',
                              }}
                            />
                          </Form.Item>

                          <Form.Item
                            name="endTime"
                            label="结束时间（秒）"
                          >
                            <Slider
                              min={0}
                              max={60}
                              step={0.1}
                              marks={{
                                0: '0s',
                                10: '10s',
                                30: '30s',
                                60: '60s',
                              }}
                            />
                          </Form.Item>
                        </>
                      ) : null
                    }}
                  </Form.Item>

                  <Form.Item
                    name="enableCrop"
                    label="启用画面裁剪"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableCrop !== currentValues.enableCrop}>
                    {({ getFieldValue }) => {
                      const enableCrop = getFieldValue('enableCrop')
                      return enableCrop ? (
                        <>
                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="cropX"
                                label="X坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="cropY"
                                label="Y坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="cropWidth"
                                label="宽度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="cropHeight"
                                label="高度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>
                        </>
                      ) : null
                    }}
                  </Form.Item>

                  <Form.Item
                    name="enableSpeed"
                    label="启用速度调整"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableSpeed !== currentValues.enableSpeed}>
                    {({ getFieldValue }) => {
                      const enableSpeed = getFieldValue('enableSpeed')
                      return enableSpeed ? (
                        <Form.Item
                          name="speed"
                          label="播放速度"
                        >
                          <Slider
                            min={0.25}
                            max={4.0}
                            step={0.25}
                            marks={{
                              0.25: '0.25x',
                              0.5: '0.5x',
                              1.0: '1.0x',
                              2.0: '2.0x',
                              4.0: '4.0x',
                            }}
                          />
                        </Form.Item>
                      ) : null
                    }}
                  </Form.Item>

                  <Form.Item
                    name="enableVolume"
                    label="启用音量调整"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableVolume !== currentValues.enableVolume}>
                    {({ getFieldValue }) => {
                      const enableVolume = getFieldValue('enableVolume')
                      return enableVolume ? (
                        <Form.Item
                          name="volume"
                          label="音量"
                        >
                          <Slider
                            min={0}
                            max={2.0}
                            step={0.1}
                            marks={{
                              0: '0',
                              0.5: '0.5',
                              1.0: '1.0',
                              1.5: '1.5',
                              2.0: '2.0',
                            }}
                          />
                        </Form.Item>
                      ) : null
                    }}
                  </Form.Item>
                </Panel>

                {/* 花字功能 */}
                <Panel header="🌸 花字" key="flower">
                  <Form.Item
                    name="enableFlower"
                    label="启用花字"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableFlower !== currentValues.enableFlower}>
                    {({ getFieldValue }) => {
                      const enableFlower = getFieldValue('enableFlower')
                      return enableFlower ? (
                        <>
                          <Form.Item
                            name="flowerText"
                            label="花字文字"
                            rules={[{ required: true, message: '请输入花字文字' }]}
                          >
                            <Input placeholder="输入要显示的文字" />
                          </Form.Item>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="flowerFont"
                                label="字体"
                              >
                                <Select>
                                  {fonts.map(font => (
                                    <Option key={font} value={font}>{font}</Option>
                                  ))}
                                </Select>
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="flowerSize"
                                label="大小"
                              >
                                <InputNumber min={10} max={200} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Form.Item
                            name="flowerColorMode"
                            label="颜色模式"
                          >
                            <Radio.Group>
                              <Radio value="单色">单色</Radio>
                              <Radio value="渐变">渐变</Radio>
                            </Radio.Group>
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.flowerColorMode !== currentValues.flowerColorMode}>
                            {({ getFieldValue }) => {
                              const colorMode = getFieldValue('flowerColorMode')
                              return colorMode === '单色' ? (
                                <Form.Item
                                  name="flowerColor"
                                  label="颜色"
                                >
                                  <ColorPicker showText />
                                </Form.Item>
                              ) : (
                                <>
                                  <Form.Item
                                    name="flowerGradientType"
                                    label="渐变类型"
                                  >
                                    <Select>
                                      <Option value="水平渐变">水平渐变</Option>
                                      <Option value="垂直渐变">垂直渐变</Option>
                                      <Option value="对角渐变">对角渐变</Option>
                                    </Select>
                                  </Form.Item>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerColorStart"
                                        label="起始颜色"
                                      >
                                        <ColorPicker showText />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerColorEnd"
                                        label="结束颜色"
                                      >
                                        <ColorPicker showText />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              )
                            }}
                          </Form.Item>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="flowerX"
                                label="X坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="flowerY"
                                label="Y坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Form.Item
                            name="flowerTimingType"
                            label="时间类型"
                          >
                            <Radio.Group>
                              <Radio value="时间戳范围">时间戳范围</Radio>
                              <Radio value="帧范围">帧范围</Radio>
                            </Radio.Group>
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.flowerTimingType !== currentValues.flowerTimingType}>
                            {({ getFieldValue }) => {
                              const timingType = getFieldValue('flowerTimingType')
                              return timingType === '时间戳范围' ? (
                                <>
                                  <Form.Item
                                    name="flowerStartTime"
                                    label="开始时间"
                                  >
                                    <Input placeholder="00:00:00" />
                                  </Form.Item>
                                  <Form.Item
                                    name="flowerEndTime"
                                    label="结束时间"
                                  >
                                    <Input placeholder="00:00:05" />
                                  </Form.Item>
                                </>
                              ) : (
                                <>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerStartFrame"
                                        label="起始帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerEndFrame"
                                        label="结束帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              )
                            }}
                          </Form.Item>

                          <Divider orientation="left" style={{ fontSize: 12 }}>描边设置</Divider>
                          <Form.Item
                            name="flowerStrokeEnabled"
                            label="启用描边"
                            valuePropName="checked"
                          >
                            <Switch />
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.flowerStrokeEnabled !== currentValues.flowerStrokeEnabled}>
                            {({ getFieldValue }) => {
                              const strokeEnabled = getFieldValue('flowerStrokeEnabled')
                              return strokeEnabled ? (
                                <>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerStrokeColor"
                                        label="描边颜色"
                                      >
                                        <ColorPicker showText />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="flowerStrokeWidth"
                                        label="描边宽度"
                                      >
                                        <InputNumber min={1} max={10} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              ) : null
                            }}
                          </Form.Item>

                          <Divider orientation="left" style={{ fontSize: 12 }}>动画设置</Divider>
                          <Form.Item
                            name="flowerAnimationEnabled"
                            label="启用动画"
                            valuePropName="checked"
                          >
                            <Switch />
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.flowerAnimationEnabled !== currentValues.flowerAnimationEnabled}>
                            {({ getFieldValue }) => {
                              const animationEnabled = getFieldValue('flowerAnimationEnabled')
                              return animationEnabled ? (
                                <>
                                  <Form.Item
                                    name="flowerAnimationType"
                                    label="动画类型"
                                  >
                                    <Select>
                                      <Option value="无效果">无效果</Option>
                                      <Option value="淡入淡出">淡入淡出</Option>
                                      <Option value="缩放">缩放</Option>
                                      <Option value="旋转">旋转</Option>
                                      <Option value="弹跳">弹跳</Option>
                                    </Select>
                                  </Form.Item>
                                  <Row gutter={16}>
                                    <Col span={8}>
                                      <Form.Item
                                        name="flowerAnimationSpeed"
                                        label="速度"
                                      >
                                        <InputNumber min={0.1} max={5.0} step={0.1} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={8}>
                                      <Form.Item
                                        name="flowerAnimationAmplitude"
                                        label="幅度"
                                      >
                                        <InputNumber min={0} max={100} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={8}>
                                      <Form.Item
                                        name="flowerAnimationDirection"
                                        label="方向"
                                      >
                                        <Select>
                                          <Option value="left">左</Option>
                                          <Option value="right">右</Option>
                                          <Option value="up">上</Option>
                                          <Option value="down">下</Option>
                                        </Select>
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              ) : null
                            }}
                          </Form.Item>
                        </>
                      ) : null
                    }}
                  </Form.Item>
                </Panel>

                {/* 插图功能 */}
                <Panel header="🖼️ 插图" key="image">
                  <Form.Item
                    name="enableImage"
                    label="启用插图"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableImage !== currentValues.enableImage}>
                    {({ getFieldValue }) => {
                      const enableImage = getFieldValue('enableImage')
                      return enableImage ? (
                        <>
                          <Form.Item
                            name="imagePath"
                            label="图片路径"
                            rules={[{ required: true, message: '请输入图片路径' }]}
                          >
                            <Input placeholder="输入图片文件的URL或本地路径" />
                          </Form.Item>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="imageX"
                                label="X坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="imageY"
                                label="Y坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="imageWidth"
                                label="宽度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="imageHeight"
                                label="高度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Form.Item
                            name="imageTimingType"
                            label="时间类型"
                          >
                            <Radio.Group>
                              <Radio value="时间戳范围">时间戳范围</Radio>
                              <Radio value="帧范围">帧范围</Radio>
                            </Radio.Group>
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.imageTimingType !== currentValues.imageTimingType}>
                            {({ getFieldValue }) => {
                              const timingType = getFieldValue('imageTimingType')
                              return timingType === '时间戳范围' ? (
                                <>
                                  <Form.Item
                                    name="imageStartTime"
                                    label="开始时间"
                                  >
                                    <Input placeholder="00:00:00" />
                                  </Form.Item>
                                  <Form.Item
                                    name="imageEndTime"
                                    label="结束时间"
                                  >
                                    <Input placeholder="00:00:05" />
                                  </Form.Item>
                                </>
                              ) : (
                                <>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="imageStartFrame"
                                        label="起始帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="imageEndFrame"
                                        label="结束帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              )
                            }}
                          </Form.Item>

                          <Form.Item
                            name="imageRemoveBg"
                            label="去除背景"
                            valuePropName="checked"
                          >
                            <Switch />
                          </Form.Item>
                        </>
                      ) : null
                    }}
                  </Form.Item>
                </Panel>

                {/* 插视频功能 */}
                <Panel header="🎬 插视频" key="video">
                  <Form.Item
                    name="enableVideo"
                    label="启用插视频"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableVideo !== currentValues.enableVideo}>
                    {({ getFieldValue }) => {
                      const enableVideo = getFieldValue('enableVideo')
                      return enableVideo ? (
                        <>
                          <Form.Item
                            name="videoPathToInsert"
                            label="视频路径"
                            rules={[{ required: true, message: '请输入视频路径' }]}
                          >
                            <Input placeholder="输入视频文件的URL或本地路径" />
                          </Form.Item>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="videoX"
                                label="X坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="videoY"
                                label="Y坐标"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="videoWidth"
                                label="宽度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="videoHeight"
                                label="高度"
                              >
                                <InputNumber min={0} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Form.Item
                            name="videoTimingType"
                            label="时间类型"
                          >
                            <Radio.Group>
                              <Radio value="时间戳范围">时间戳范围</Radio>
                              <Radio value="帧范围">帧范围</Radio>
                            </Radio.Group>
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.videoTimingType !== currentValues.videoTimingType}>
                            {({ getFieldValue }) => {
                              const timingType = getFieldValue('videoTimingType')
                              return timingType === '时间戳范围' ? (
                                <>
                                  <Form.Item
                                    name="videoStartTime"
                                    label="开始时间"
                                  >
                                    <Input placeholder="00:00:00" />
                                  </Form.Item>
                                  <Form.Item
                                    name="videoEndTime"
                                    label="结束时间"
                                  >
                                    <Input placeholder="99:59:59" />
                                  </Form.Item>
                                </>
                              ) : (
                                <>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="videoStartFrame"
                                        label="起始帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="videoEndFrame"
                                        label="结束帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              )
                            }}
                          </Form.Item>
                        </>
                      ) : null
                    }}
                  </Form.Item>
                </Panel>

                {/* 水印功能 */}
                <Panel header="©️ 水印" key="watermark">
                  <Form.Item
                    name="enableWatermark"
                    label="启用水印"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableWatermark !== currentValues.enableWatermark}>
                    {({ getFieldValue }) => {
                      const enableWatermark = getFieldValue('enableWatermark')
                      return enableWatermark ? (
                        <>
                          <Form.Item
                            name="watermarkText"
                            label="水印文字"
                            rules={[{ required: true, message: '请输入水印文字' }]}
                          >
                            <Input placeholder="输入水印文字" />
                          </Form.Item>

                          <Row gutter={16}>
                            <Col span={12}>
                              <Form.Item
                                name="watermarkFont"
                                label="字体"
                              >
                                <Select>
                                  {fonts.map(font => (
                                    <Option key={font} value={font}>{font}</Option>
                                  ))}
                                </Select>
                              </Form.Item>
                            </Col>
                            <Col span={12}>
                              <Form.Item
                                name="watermarkSize"
                                label="大小"
                              >
                                <InputNumber min={10} max={100} style={{ width: '100%' }} />
                              </Form.Item>
                            </Col>
                          </Row>

                          <Form.Item
                            name="watermarkColor"
                            label="颜色"
                          >
                            <ColorPicker showText />
                          </Form.Item>

                          <Form.Item
                            name="watermarkStyle"
                            label="样式"
                          >
                            <Select>
                              <Option value="半透明浮动">半透明浮动</Option>
                              <Option value="固定位置">固定位置</Option>
                              <Option value="滚动显示">滚动显示</Option>
                            </Select>
                          </Form.Item>

                          <Form.Item
                            name="watermarkTimingType"
                            label="时间类型"
                          >
                            <Radio.Group>
                              <Radio value="时间戳范围">时间戳范围</Radio>
                              <Radio value="帧范围">帧范围</Radio>
                            </Radio.Group>
                          </Form.Item>

                          <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.watermarkTimingType !== currentValues.watermarkTimingType}>
                            {({ getFieldValue }) => {
                              const timingType = getFieldValue('watermarkTimingType')
                              return timingType === '时间戳范围' ? (
                                <>
                                  <Form.Item
                                    name="watermarkStartTime"
                                    label="开始时间"
                                  >
                                    <Input placeholder="00:00:00" />
                                  </Form.Item>
                                  <Form.Item
                                    name="watermarkEndTime"
                                    label="结束时间"
                                  >
                                    <Input placeholder="99:59:59" />
                                  </Form.Item>
                                </>
                              ) : (
                                <>
                                  <Row gutter={16}>
                                    <Col span={12}>
                                      <Form.Item
                                        name="watermarkStartFrame"
                                        label="起始帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                    <Col span={12}>
                                      <Form.Item
                                        name="watermarkEndFrame"
                                        label="结束帧"
                                      >
                                        <InputNumber min={0} style={{ width: '100%' }} />
                                      </Form.Item>
                                    </Col>
                                  </Row>
                                </>
                              )
                            }}
                          </Form.Item>
                        </>
                      ) : null
                    }}
                  </Form.Item>
                </Panel>
              </Collapse>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<ScissorOutlined />}
                  loading={loading}
                  block
                >
                  应用效果
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
                    <ScissorOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>编辑后的视频将在这里显示</p>
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

export default VideoEditor