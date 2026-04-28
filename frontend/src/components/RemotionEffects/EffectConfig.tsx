import React, { useState, useEffect } from 'react'
import { Card, Form, Input, InputNumber, Select, Switch, ColorPicker, Spin, message } from 'antd'
import { SettingOutlined } from '@ant-design/icons'
import { remotionApi } from '../../services/remotionApi'

const { Option } = Select

interface EffectConfigProps {
  projectId?: string
  onChange?: (params: Record<string, any>) => void
  initialValues?: Record<string, any>
}

const EffectConfig: React.FC<EffectConfigProps> = ({
  projectId,
  onChange,
  initialValues,
}) => {
  const [form] = Form.useForm()
  const [params, setParams] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadParams()
    }
  }, [projectId])

  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues)
    }
  }, [initialValues, form])

  const loadParams = async () => {
    try {
      setLoading(true)
      const data = await remotionApi.getProjects()
      const project = data.find((p) => p.id === projectId)
      if (project) {
        setParams({})
      }
    } catch (error) {
      message.error('加载参数定义失败')
    } finally {
      setLoading(false)
    }
  }

  const handleValuesChange = (_: any, allValues: Record<string, any>) => {
    if (onChange) {
      onChange(allValues)
    }
  }

  return (
    <Card title="特效配置" extra={<SettingOutlined />}>
      <Spin spinning={loading}>
        <Form
          form={form}
          layout="vertical"
          onValuesChange={handleValuesChange}
          initialValues={{
            width: 720,
            height: 1280,
            fps: 24,
            duration: 10,
            words: ['福', '禄', '寿'],
          }}
        >
          <Form.Item label="视频宽度" name="width">
            <InputNumber min={480} max={1920} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="视频高度" name="height">
            <InputNumber min={480} max={2160} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="帧率" name="fps">
            <Select>
              <Option value={24}>24 FPS</Option>
              <Option value={30}>30 FPS</Option>
              <Option value={60}>60 FPS</Option>
            </Select>
          </Form.Item>

          <Form.Item label="视频时长（秒）" name="duration">
            <InputNumber min={1} max={60} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="文字列表" name="words">
            <Select mode="tags" placeholder="输入文字，按回车添加" />
          </Form.Item>
        </Form>
      </Spin>
    </Card>
  )
}

export default EffectConfig