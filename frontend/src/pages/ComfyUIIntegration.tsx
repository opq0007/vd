import React, { useState } from 'react'
import { Card, Form, Input, Button, message, Space, Row, Col, Divider, Select, Slider } from 'antd'
import { PictureOutlined, PlayCircleOutlined } from '@ant-design/icons'

const { TextArea } = Input
const { Option } = Select

interface ComfyUIConfig {
  prompt: string
  negativePrompt: string
  width: number
  height: number
  steps: number
  cfgScale: number
  seed?: number
}

const ComfyUIIntegration: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)

  const handleGenerate = async (values: ComfyUIConfig) => {
    if (!values.prompt) {
      message.warning('请输入提示词')
      return
    }

    setLoading(true)
    try {
      const workflowJson = JSON.stringify({
        "3": {
          "inputs": {
            "seed": values.seed || 0,
            "steps": values.steps,
            "cfg": values.cfgScale,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
          },
          "class_type": "KSampler"
        },
        "4": {
          "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.ckpt"
          },
          "class_type": "CheckpointLoaderSimple"
        },
        "5": {
          "inputs": {
            "width": values.width,
            "height": values.height,
            "batch_size": 1
          },
          "class_type": "EmptyLatentImage"
        },
        "6": {
          "inputs": {
            "text": values.prompt,
            "clip": ["4", 1]
          },
          "class_type": "CLIPTextEncode"
        },
        "7": {
          "inputs": {
            "text": values.negativePrompt || "",
            "clip": ["4", 1]
          },
          "class_type": "CLIPTextEncode"
        },
        "8": {
          "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
          },
          "class_type": "VAEDecode"
        },
        "9": {
          "inputs": {
            "filename_prefix": "ComfyUI",
            "images": ["8", 0]
          },
          "class_type": "SaveImage"
        }
      })

      const formData = new FormData()
      formData.append('workflow_json', workflowJson)
      formData.append('timeout', '300')

      const response = await fetch('/api/comfyui/execute', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        const imagePath = data.data?.images?.[0]?.filename
        if (imagePath) {
          setImageUrl(`/api/file/download?file_path=${imagePath}`)
        }
        message.success('图像生成成功')
      } else {
        message.error(data.error || data.message)
      }
    } catch (error) {
      message.error('图像生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="🎨 ComfyUI 集成" extra={<PictureOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleGenerate}
          initialValues={{
            width: 512,
            height: 512,
            steps: 20,
            cfgScale: 7.0,
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📝 提示词</Divider>
              <Form.Item
                name="prompt"
                label="正向提示词"
                rules={[{ required: true, message: '请输入正向提示词' }]}
              >
                <TextArea
                  rows={4}
                  placeholder="描述你想要生成的图像内容..."
                />
              </Form.Item>

              <Form.Item
                name="negativePrompt"
                label="负向提示词"
              >
                <TextArea
                  rows={2}
                  placeholder="描述你不想要在图像中出现的内容..."
                />
              </Form.Item>

              <Divider orientation="left">⚙️ 参数配置</Divider>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="width"
                    label="宽度"
                  >
                    <Select>
                      <Option value={512}>512</Option>
                      <Option value={768}>768</Option>
                      <Option value={1024}>1024</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="height"
                    label="高度"
                  >
                    <Select>
                      <Option value={512}>512</Option>
                      <Option value={768}>768</Option>
                      <Option value={1024}>1024</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="steps"
                label="采样步数"
              >
                <Slider
                  min={10}
                  max={50}
                  step={1}
                  marks={{
                    10: '10',
                    20: '20',
                    30: '30',
                    50: '50',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="cfgScale"
                label="CFG Scale"
                tooltip="控制提示词的强度"
              >
                <Slider
                  min={1}
                  max={20}
                  step={0.5}
                  marks={{
                    1: '1',
                    7: '7',
                    10: '10',
                    20: '20',
                  }}
                />
              </Form.Item>

              <Form.Item
                name="seed"
                label="随机种子（可选）"
              >
                <Input type="number" placeholder="留空则随机生成" />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PictureOutlined />}
                  loading={loading}
                  block
                >
                  生成图像
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">👁️ 生成结果</Divider>
              {imageUrl ? (
                <Card size="small">
                  <img
                    src={imageUrl}
                    alt="生成的图像"
                    style={{ width: '100%', borderRadius: 8 }}
                  />
                  <Space style={{ marginTop: 16, width: '100%', justifyContent: 'center' }}>
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={() => window.open(imageUrl, '_blank')}
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
                    <p>生成的图像将在这里显示</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📋 使用说明</Divider>
        <Card size="small">
          <h4>提示词技巧：</h4>
          <ul>
            <li>使用具体的描述词，如"a beautiful sunset over the ocean"</li>
            <li>添加风格关键词，如"photorealistic", "digital art", "oil painting"</li>
            <li>使用负向提示词排除不需要的元素，如"blurry, low quality"</li>
          </ul>
          <h4>参数说明：</h4>
          <ul>
            <li><strong>采样步数</strong>：步数越多，质量越高，但生成时间越长</li>
            <li><strong>CFG Scale</strong>：值越高，越严格遵循提示词</li>
            <li><strong>随机种子</strong>：固定种子可以重现相同的生成结果</li>
          </ul>
        </Card>
      </Card>
    </div>
  )
}

export default ComfyUIIntegration