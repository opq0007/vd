import React, { useState } from 'react'
import { Card, Form, Input, Button, Select, Checkbox, Slider, Radio, message, Row, Col, Divider, Tag, Upload } from 'antd'
import { VideoCameraOutlined, AudioOutlined, FileTextOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactPlayer from 'react-player'

const { TextArea } = Input
const { Option } = Select

interface SubtitleConfig {
  inputType: 'upload' | 'path'
  videoFile: any[]
  audioFile: any[]
  subtitleFile: any[]
  videoPath?: string
  audioPath?: string
  subtitlePath?: string
  modelName: string
  device: string
  generateSubtitle: boolean
  bilingual: boolean
  wordTimestamps: boolean
  burnType: 'none' | 'hard'
  beamSize: number
  subtitleBottomMargin: number
  durationReference: 'video' | 'audio'
  adjustAudioSpeed: boolean
  audioSpeedFactor: number
  audioVolume: number
  keepOriginalAudio: boolean
  enableLLMCorrection: boolean
  referenceText?: string
  vadFilter: boolean
  conditionOnPreviousText: boolean
  temperature: number
  maxCharsPerLine: number
  maxLinesPerSegment: number
}

const SubtitleGeneration: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [status, setStatus] = useState<string>('')

  const handleGenerate = async (values: SubtitleConfig) => {
    setLoading(true)
    setStatus('正在生成字幕...')
    try {
      const formData = new FormData()
      formData.append('input_type', values.inputType)
      formData.append('model_name', values.modelName)
      formData.append('device', values.device)
      formData.append('generate_subtitle', values.generateSubtitle.toString())
      formData.append('bilingual', values.bilingual.toString())
      formData.append('word_timestamps', values.wordTimestamps.toString())
      formData.append('burn_subtitles', values.burnType)
      formData.append('beam_size', values.beamSize.toString())
      formData.append('subtitle_bottom_margin', values.subtitleBottomMargin.toString())
      formData.append('duration_reference', values.durationReference)
      formData.append('adjust_audio_speed', values.adjustAudioSpeed.toString())
      formData.append('audio_speed_factor', values.audioSpeedFactor.toString())
      formData.append('audio_volume', values.audioVolume.toString())
      formData.append('keep_original_audio', values.keepOriginalAudio.toString())
      formData.append('enable_llm_correction', values.enableLLMCorrection.toString())
      formData.append('vad_filter', values.vadFilter.toString())
      formData.append('condition_on_previous_text', values.conditionOnPreviousText.toString())
      formData.append('temperature', values.temperature.toString())
      formData.append('max_chars_per_line', values.maxCharsPerLine.toString())
      formData.append('max_lines_per_segment', values.maxLinesPerSegment.toString())

      if (values.inputType === 'upload') {
        if (values.videoFile && values.videoFile.length > 0) {
          const videoFile = values.videoFile[0]?.originFileObj
          if (videoFile) {
            formData.append('video_file', videoFile)
          }
        }
        if (values.audioFile && values.audioFile.length > 0) {
          const audioFile = values.audioFile[0]?.originFileObj
          if (audioFile) {
            formData.append('audio_file', audioFile)
          }
        }
        if (values.subtitleFile && values.subtitleFile.length > 0) {
          const subtitleFile = values.subtitleFile[0]?.originFileObj
          if (subtitleFile) {
            formData.append('subtitle_file', subtitleFile)
          }
        }
      } else {
        if (values.videoPath) formData.append('video_path', values.videoPath)
        if (values.audioPath) formData.append('audio_path', values.audioPath)
        if (values.subtitlePath) formData.append('subtitle_path', values.subtitlePath)
      }

      if (values.referenceText) {
        formData.append('reference_text', values.referenceText)
      }

      const response = await fetch('/api/subtitle/generate', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        setResult(data)
        setStatus(`处理完成！生成字幕片段数: ${data.segments_count}`)
        message.success('字幕生成成功')
      } else {
        setStatus(`处理失败: ${data.error}`)
        message.error(data.error)
      }
    } catch (error) {
      setStatus(`处理失败: ${error instanceof Error ? error.message : '未知错误'}`)
      message.error('字幕生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="📝 高级字幕生成" extra={<FileTextOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleGenerate}
          initialValues={{
            inputType: 'upload',
            modelName: 'small',
            device: 'cpu',
            generateSubtitle: true,
            bilingual: false,
            wordTimestamps: false,
            burnType: 'none',
            beamSize: 5,
            subtitleBottomMargin: 50,
            durationReference: 'video',
            adjustAudioSpeed: false,
            audioSpeedFactor: 1.0,
            audioVolume: 1.0,
            keepOriginalAudio: true,
            enableLLMCorrection: false,
            vadFilter: true,
            conditionOnPreviousText: true,
            temperature: 0.0,
            maxCharsPerLine: 20,
            maxLinesPerSegment: 2,
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 上传文件</Divider>
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
                      >
                        <Upload.Dragger
                          accept="video/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <VideoCameraOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽视频文件到此处</p>
                        </Upload.Dragger>
                      </Form.Item>

                      <Form.Item
                        name="audioFile"
                        label="音频文件"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                      >
                        <Upload.Dragger
                          accept="audio/*"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <AudioOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽音频文件到此处</p>
                        </Upload.Dragger>
                      </Form.Item>

                      <Form.Item
                        name="subtitleFile"
                        label="字幕文件（可选）"
                        valuePropName="fileList"
                        getValueFromEvent={(e) => e && e.fileList}
                      >
                        <Upload.Dragger
                          accept=".srt,.vtt,.ass,.ssa"
                          maxCount={1}
                          beforeUpload={() => false}
                        >
                          <p className="ant-upload-drag-icon">
                            <FileTextOutlined />
                          </p>
                          <p className="ant-upload-text">点击或拖拽字幕文件到此处</p>
                        </Upload.Dragger>
                      </Form.Item>
                    </>
                  ) : (
                    <>
                      <Form.Item
                        name="videoPath"
                        label="视频文件路径"
                      >
                        <Input placeholder="输入视频文件的URL或本地路径" />
                      </Form.Item>

                      <Form.Item
                        name="audioPath"
                        label="音频文件路径"
                      >
                        <Input placeholder="输入音频文件的URL或本地路径" />
                      </Form.Item>

                      <Form.Item
                        name="subtitlePath"
                        label="字幕文件路径"
                      >
                        <Input placeholder="输入字幕文件的URL或本地路径" />
                      </Form.Item>
                    </>
                  )
                }}
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">⚙️ 字幕参数</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="modelName"
                    label="Whisper 模型"
                  >
                    <Select>
                      <Option value="tiny">tiny</Option>
                      <Option value="base">base</Option>
                      <Option value="small">small</Option>
                      <Option value="medium">medium</Option>
                      <Option value="large">large</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="device"
                    label="设备选择"
                  >
                    <Select>
                      <Option value="cpu">cpu</Option>
                      <Option value="cuda">cuda</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="generateSubtitle"
                    valuePropName="checked"
                  >
                    <Checkbox>生成字幕</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="bilingual"
                    valuePropName="checked"
                  >
                    <Checkbox>双语字幕</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="wordTimestamps"
                    valuePropName="checked"
                  >
                    <Checkbox>词级时间戳</Checkbox>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">🎯 Whisper 参数</Divider>
              <Form.Item
                name="vadFilter"
                valuePropName="checked"
              >
                <Checkbox>启用 VAD 语音活动检测</Checkbox>
              </Form.Item>

              <Form.Item
                name="conditionOnPreviousText"
                valuePropName="checked"
              >
                <Checkbox>不依赖前文分段</Checkbox>
              </Form.Item>

              <Form.Item
                name="temperature"
                label="温度参数"
                tooltip="控制预测的随机性，0 表示更保守（推荐），1 表示更随机"
              >
                <Slider
                  min={0.0}
                  max={1.0}
                  step={0.1}
                  marks={{
                    0.0: '0.0',
                    0.5: '0.5',
                    1.0: '1.0',
                  }}
                />
              </Form.Item>

              <Divider orientation="left">📝 字幕显示参数</Divider>
              <Form.Item
                name="maxCharsPerLine"
                label="每行最大字符数"
              >
                <Slider
                  min={10}
                  max={30}
                  step={2}
                  marks={{
                    10: '10',
                    20: '20',
                    30: '30',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="maxLinesPerSegment"
                label="每段最大行数"
              >
                <Slider
                  min={1}
                  max={4}
                  step={1}
                  marks={{
                    1: '1',
                    2: '2',
                    3: '3',
                    4: '4',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="burnType"
                label="字幕烧录类型"
              >
                <Radio.Group>
                  <Radio value="none">不烧录</Radio>
                  <Radio value="hard">硬烧录</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item
                name="subtitleBottomMargin"
                label="字幕下沿距离（像素）"
              >
                <Slider
                  min={0}
                  max={500}
                  step={1}
                  marks={{
                    0: '0',
                    50: '50',
                    100: '100',
                    500: '500',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="durationReference"
                label="时长基准"
              >
                <Radio.Group>
                  <Radio value="video">视频</Radio>
                  <Radio value="audio">音频</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item
                name="adjustAudioSpeed"
                valuePropName="checked"
              >
                <Checkbox>自动调整音频语速</Checkbox>
              </Form.Item>

              <Form.Item
                name="audioSpeedFactor"
                label="语速调整倍数"
              >
                <Slider
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  marks={{
                    0.5: '0.5x',
                    1.0: '1.0x',
                    1.5: '1.5x',
                    2.0: '2.0x',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="audioVolume"
                label="音频音量"
              >
                <Slider
                  min={0.0}
                  max={3.0}
                  step={0.1}
                  marks={{
                    0.0: '0.0',
                    1.0: '1.0',
                    2.0: '2.0',
                    3.0: '3.0',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="keepOriginalAudio"
                valuePropName="checked"
              >
                <Checkbox>保留原视频音频</Checkbox>
              </Form.Item>

              <Divider orientation="left">🤖 LLM 字幕纠错</Divider>
              <Form.Item
                name="enableLLMCorrection"
                valuePropName="checked"
              >
                <Checkbox>启用 LLM 字幕纠错</Checkbox>
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.enableLLMCorrection !== currentValues.enableLLMCorrection}>
                {({ getFieldValue }) => {
                  const enableLLMCorrection = getFieldValue('enableLLMCorrection')

                  return enableLLMCorrection ? (
                    <Form.Item
                      name="referenceText"
                      label="参考文本"
                    >
                      <TextArea
                        rows={5}
                        placeholder="输入正确的文本内容，用于纠正字幕中的错字、漏字、多字等错误..."
                      />
                    </Form.Item>
                  ) : null
                }}
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<FileTextOutlined />}
                  loading={loading}
                  block
                >
                  生成字幕
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📝 转录结果</Divider>
        {status && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Tag color={status.includes('完成') ? 'success' : 'error'}>
              {status}
            </Tag>
          </Card>
        )}

        {result && (
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card title="📄 字幕文件" size="small">
                {result.subtitle_path && (
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    href={result.subtitle_path}
                    download
                  >
                    下载SRT字幕文件
                  </Button>
                )}
                {result.bilingual_subtitle_path && (
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    href={result.bilingual_subtitle_path}
                    download
                  >
                    下载双语SRT字幕文件
                  </Button>
                )}
              </Card>
            </Col>

            <Col xs={24} md={12}>
              <Card title="🎬 视频预览" size="small">
                {result.video_with_subtitle_path && (
                  <ReactPlayer
                    url={result.video_with_subtitle_path}
                    controls
                    width="100%"
                    height={200}
                  />
                )}
              </Card>
            </Col>

            <Col span={24}>
              <Card title="📥 视频文件" size="small">
                {result.video_with_subtitle_path && (
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    href={result.video_with_subtitle_path}
                    download
                  >
                    下载处理后的视频文件
                  </Button>
                )}
              </Card>
            </Col>

            <Col span={24}>
              <Card title="📝 转录文本" size="small">
                <TextArea
                  value={result.transcript_text || ''}
                  rows={10}
                  readOnly
                />
              </Card>
            </Col>
          </Row>
        )}
      </Card>
    </div>
  )
}

export default SubtitleGeneration