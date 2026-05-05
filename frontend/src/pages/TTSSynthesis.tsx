import React, { useState } from 'react'
import { Card, Form, Input, Button, Slider, Radio, message, Space, Row, Col, Divider, List, Tag } from 'antd'
import { AudioOutlined, SaveOutlined, PlayCircleOutlined, SoundOutlined } from '@ant-design/icons'
import ReactPlayer from 'react-player'

const { TextArea } = Input

interface TTSConfig {
  text: string
  refInputType: 'upload' | 'path' | 'feature'
  refAudioFile?: File
  refAudioPath?: string
  featureId?: string
  promptText?: string
  cfgValue: number
  inferenceTimesteps: number
  maxLen: number
}

const TTSSynthesis: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [features, setFeatures] = useState<any[]>([])

  const handleSynthesize = async (values: TTSConfig) => {
    setLoading(true)
    setStatus('正在生成语音...')
    try {
      const formData = new FormData()
      formData.append('text', values.text)
      formData.append('cfg_value', values.cfgValue.toString())
      formData.append('timesteps', values.inferenceTimesteps.toString())
      formData.append('min_len', '2')
      formData.append('max_len', values.maxLen.toString())

      if (values.refInputType === 'upload' && values.refAudioFile) {
        formData.append('prompt_wav', values.refAudioFile)
      } else if (values.refInputType === 'path' && values.refAudioPath) {
        formData.append('prompt_wav_path', values.refAudioPath)
      } else if (values.refInputType === 'feature' && values.featureId) {
        formData.append('feat_id', values.featureId)
      }

      if (values.promptText) {
        formData.append('prompt_text', values.promptText)
      }

      const response = await fetch('/api/tts/synthesize', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.success) {
        const audioPath = result.data?.output_path || result.output_path
        if (audioPath) {
          setAudioUrl(`/api/file/download?file_path=${audioPath}`)
        }
        setStatus(`语音合成成功！`)
        message.success('语音合成成功')
      } else {
        setStatus(`合成失败: ${result.error || result.message}`)
        message.error(result.error || result.message)
      }
    } catch (error) {
      setStatus(`合成失败: ${error instanceof Error ? error.message : '未知错误'}`)
      message.error('语音合成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveFeature = async () => {
    const values = form.getFieldsValue()
    if (!values.refAudioFile) {
      message.warning('请先上传参考音频')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('prompt_wav_upload', values.refAudioFile)
      formData.append('feat_id', values.featureId || '')
      formData.append('prompt_text', values.promptText || '')

      const response = await fetch('/api/tts/save-ref-audio', {
        method: 'POST',
        body: formData,
      })

      const result = await response.json()

      if (result.success) {
        message.success(`参考音频特征保存成功！特征 ID: ${values.featureId}`)
        handleListFeatures()
      } else {
        message.error(result.error)
      }
    } catch (error) {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleListFeatures = async () => {
    try {
      const response = await fetch('/api/tts/ref_features')
      const result = await response.json()

      if (result.success) {
        setFeatures(result.data?.features || [])
      }
    } catch (error) {
      message.error('获取特征列表失败')
    }
  }

  return (
    <div>
      <Card title="🎤 VoxCPM-1.5 语音合成 (ONNX)" extra={<SoundOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSynthesize}
          initialValues={{
            refInputType: 'upload',
            cfgValue: 2.0,
            inferenceTimesteps: 5,
            maxLen: 2000,
            text: '你好，这是一个测试文本。',
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📝 输入文本</Divider>
              <Form.Item
                name="text"
                label="目标文本"
                rules={[{ required: true, message: '请输入要合成的文本' }]}
              >
                <TextArea
                  rows={3}
                  placeholder="请输入要合成的文本..."
                />
              </Form.Item>

              <Divider orientation="left">🎵 参考音频（可选）</Divider>
              <Form.Item
                name="refInputType"
                label="参考音频输入方式"
              >
                <Radio.Group>
                  <Radio value="upload">上传文件</Radio>
                  <Radio value="path">路径方式</Radio>
                  <Radio value="feature">预编码特征</Radio>
                </Radio.Group>
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.refInputType !== currentValues.refInputType}>
                {({ getFieldValue }) => {
                  const refInputType = getFieldValue('refInputType')

                  return (
                    <>
                      {refInputType === 'upload' && (
                        <>
                          <Form.Item
                            name="refAudioFile"
                            label="参考音频"
                            valuePropName="fileList"
                            getValueFromEvent={(e) => e && e.fileList}
                          >
                            <input
                              type="file"
                              accept="audio/*"
                              onChange={(e) => {
                                const file = e.target.files?.[0]
                                if (file) {
                                  form.setFieldsValue({ refAudioFile: file })
                                }
                              }}
                            />
                          </Form.Item>
                          <Form.Item
                            name="featureId"
                            label="特征 ID"
                          >
                            <Input placeholder="输入特征 ID 以保存或使用预编码特征" />
                          </Form.Item>
                          <Button
                            type="default"
                            icon={<SaveOutlined />}
                            onClick={handleSaveFeature}
                            loading={loading}
                            style={{ marginBottom: 16 }}
                          >
                            保存为预编码特征
                          </Button>
                        </>
                      )}

                      {refInputType === 'path' && (
                        <Form.Item
                          name="refAudioPath"
                          label="参考音频路径"
                        >
                          <Input placeholder="请输入音频文件路径或URL" />
                        </Form.Item>
                      )}

                      {refInputType === 'feature' && (
                        <Form.Item
                          name="featureId"
                          label="特征 ID"
                          rules={[{ required: true, message: '请输入特征 ID' }]}
                        >
                          <Input placeholder="输入已保存的特征 ID" />
                        </Form.Item>
                      )}
                    </>
                  )
                }}
              </Form.Item>

              <Form.Item
                name="promptText"
                label="参考文本"
              >
                <TextArea
                  rows={2}
                  placeholder="如果上传了参考音频，可以输入对应的文本..."
                />
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">⚙️ 参数配置</Divider>
              <Form.Item
                name="cfgValue"
                label="CFG值（引导强度）"
                tooltip="控制生成语音与目标文本的匹配程度"
              >
                <Slider
                  min={1.0}
                  max={3.0}
                  step={0.1}
                  marks={{
                    1.0: '1.0',
                    2.0: '2.0',
                    3.0: '3.0',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="inferenceTimesteps"
                label="推理步数"
                tooltip="影响生成质量和速度的平衡（默认 5）"
              >
                <Slider
                  min={4}
                  max={30}
                  step={1}
                  marks={{
                    4: '4',
                    10: '10',
                    20: '20',
                    30: '30',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="maxLen"
                label="最大生成长度"
                tooltip="控制生成音频的最大长度"
              >
                <Slider
                  min={100}
                  max={5000}
                  step={100}
                  marks={{
                    100: '100',
                    1000: '1000',
                    2000: '2000',
                    5000: '5000',
                  }}
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<AudioOutlined />}
                    loading={loading}
                  >
                    生成语音
                  </Button>
                  <Button
                    icon={<PlayCircleOutlined />}
                    onClick={handleListFeatures}
                  >
                    查看所有特征 ID
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📤 输出结果</Divider>
        {status && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Tag color={status.includes('成功') ? 'success' : 'error'}>
              {status}
            </Tag>
          </Card>
        )}

        {audioUrl && (
          <Card title="生成的语音" size="small">
            <ReactPlayer
              url={audioUrl}
              controls
              width="100%"
              height={50}
            />
          </Card>
        )}

        {features.length > 0 && (
          <Card title="📋 已保存的特征" size="small" style={{ marginTop: 16 }}>
            <List
              dataSource={features}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={`特征 ID: ${item.feat_id}`}
                    description={`参考文本: ${item.prompt_text} | Patch Size: ${item.patch_size} | 创建时间: ${item.created_at}`}
                  />
                </List.Item>
              )}
            />
          </Card>
        )}
      </Card>
    </div>
  )
}

export default TTSSynthesis