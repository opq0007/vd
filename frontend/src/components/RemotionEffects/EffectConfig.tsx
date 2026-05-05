import React, { useState, useEffect } from 'react'
import { Card, Form, Input, InputNumber, Select, Switch, message, Spin } from 'antd'
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
  const [projectParams, setProjectParams] = useState<any>(null)

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
      const data = await remotionApi.getProjectParams(projectId || '')
      setProjectParams(data)
      setParams(data.params || {})
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

  const renderFormField = (paramName: string, paramDef: any) => {
    const { type, defaultValue, description, required } = paramDef

    const label = description || paramName
    const rules = required ? [{ required: true, message: `请输入${label}` }] : []

    switch (type) {
      case 'string':
        return (
          <Form.Item key={paramName} label={label} name={paramName} rules={rules}>
            <Input placeholder={label} />
          </Form.Item>
        )

      case 'number':
        return (
          <Form.Item key={paramName} label={label} name={paramName} rules={rules}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        )

      case 'boolean':
        return (
          <Form.Item key={paramName} label={label} name={paramName} valuePropName="checked">
            <Switch />
          </Form.Item>
        )

      case 'array':
        if (paramName === 'dreams') {
          return (
            <Form.Item key={paramName} label={label} name={paramName} rules={rules}>
              <Select mode="multiple" placeholder="选择梦想职业">
                <Option value="astronaut">宇航员</Option>
                <Option value="artist">艺术家</Option>
                <Option value="racer">赛车手</Option>
                <Option value="doctor">医生</Option>
                <Option value="teacher">老师</Option>
                <Option value="scientist">科学家</Option>
                <Option value="musician">音乐家</Option>
                <Option value="athlete">运动员</Option>
                <Option value="chef">厨师</Option>
                <Option value="pilot">飞行员</Option>
              </Select>
            </Form.Item>
          )
        }
        return (
          <Form.Item key={paramName} label={label} name={paramName} rules={rules}>
            <Select mode="tags" placeholder="输入内容，按回车添加" />
          </Form.Item>
        )

      case 'select':
        return (
          <Form.Item key={paramName} label={label} name={paramName} rules={rules}>
            <Select placeholder={label}>
              {paramDef.options?.map((opt: any) => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Form.Item>
        )

      default:
        return null
    }
  }

  const renderPresetSelector = () => {
    if (!projectParams?.presets || Object.keys(projectParams.presets).length === 0) {
      return null
    }

    return (
      <Form.Item label="预设模板" name="_preset">
        <Select placeholder="选择预设模板">
          {Object.entries(projectParams.presets).map(([key, preset]: [string, any]) => (
            <Option key={key} value={key}>
              {preset.name} - {preset.description}
            </Option>
          ))}
        </Select>
      </Form.Item>
    )
  }

  const handlePresetChange = (presetKey: string) => {
    if (!projectParams?.presets || !presetKey) return

    const preset = projectParams.presets[presetKey]
    if (preset) {
      form.setFieldsValue(preset)
    }
  }

  return (
    <Card title="特效配置" extra={<SettingOutlined />}>
      <Spin spinning={loading}>
        <Form
          form={form}
          layout="vertical"
          onValuesChange={handleValuesChange}
          initialValues={initialValues}
        >
          {renderPresetSelector()}

          {projectParams && Object.entries(projectParams.params).map(([paramName, paramDef]) =>
            renderFormField(paramName, paramDef)
          )}
        </Form>
      </Spin>
    </Card>
  )
}

export default EffectConfig