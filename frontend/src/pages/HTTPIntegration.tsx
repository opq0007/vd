import React, { useState } from 'react'
import { Card, Form, Input, Button, Select, message, Space, Row, Col, Divider, Table, Tag } from 'antd'
import { ApiOutlined } from '@ant-design/icons'

const { TextArea } = Input
const { Option } = Select

interface HTTPIntegrationConfig {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  headers: Record<string, string>
  body?: string
  authType: 'none' | 'basic' | 'bearer' | 'api-key'
  username?: string
  password?: string
  token?: string
  apiKey?: string
}

const HTTPIntegration: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])

  const handleSend = async (values: HTTPIntegrationConfig) => {
    if (!values.url) {
      message.warning('请输入URL')
      return
    }

    setLoading(true)
    try {
      const headers: Record<string, string> = { ...values.headers }

      if (values.authType === 'basic' && values.username && values.password) {
        const auth = btoa(`${values.username}:${values.password}`)
        headers['Authorization'] = `Basic ${auth}`
      } else if (values.authType === 'bearer' && values.token) {
        headers['Authorization'] = `Bearer ${values.token}`
      } else if (values.authType === 'api-key' && values.apiKey) {
        headers['X-API-Key'] = values.apiKey
      }

      const response = await fetch(values.url, {
        method: values.method,
        headers,
        body: values.method !== 'GET' ? values.body : undefined,
      })

      const data = await response.json()

      setResult({
        status: response.status,
        statusText: response.statusText,
        data,
      })

      setHistory([
        {
          id: Date.now(),
          url: values.url,
          method: values.method,
          status: response.status,
          timestamp: new Date().toISOString(),
        },
        ...history,
      ])

      message.success('请求发送成功')
    } catch (error) {
      message.error('请求发送失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      render: (method: string) => (
        <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : 'orange'}>
          {method}
        </Tag>
      ),
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: number) => (
        <Tag color={status >= 200 && status < 300 ? 'success' : 'error'}>
          {status}
        </Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp: string) => new Date(timestamp).toLocaleString(),
    },
  ]

  return (
    <div>
      <Card title="🌐 HTTP 集成" extra={<ApiOutlined />}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSend}
          initialValues={{
            method: 'POST',
            authType: 'none',
            headers: {},
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Divider orientation="left">📤 请求配置</Divider>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="method"
                    label="请求方法"
                  >
                    <Select>
                      <Option value="GET">GET</Option>
                      <Option value="POST">POST</Option>
                      <Option value="PUT">PUT</Option>
                      <Option value="DELETE">DELETE</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={16}>
                  <Form.Item
                    name="url"
                    label="URL"
                    rules={[{ required: true, message: '请输入URL' }]}
                  >
                    <Input placeholder="https://api.example.com/endpoint" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="authType"
                label="认证方式"
              >
                <Select>
                  <Option value="none">无认证</Option>
                  <Option value="basic">Basic Auth</Option>
                  <Option value="bearer">Bearer Token</Option>
                  <Option value="api-key">API Key</Option>
                </Select>
              </Form.Item>

              <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.authType !== currentValues.authType}>
                {({ getFieldValue }) => {
                  const authType = getFieldValue('authType')

                  return authType === 'basic' ? (
                    <>
                      <Form.Item
                        name="username"
                        label="用户名"
                      >
                        <Input placeholder="用户名" />
                      </Form.Item>
                      <Form.Item
                        name="password"
                        label="密码"
                      >
                        <Input.Password placeholder="密码" />
                      </Form.Item>
                    </>
                  ) : authType === 'bearer' ? (
                    <Form.Item
                      name="token"
                      label="Bearer Token"
                    >
                      <Input placeholder="Bearer token" />
                    </Form.Item>
                  ) : authType === 'api-key' ? (
                    <Form.Item
                      name="apiKey"
                      label="API Key"
                    >
                      <Input placeholder="API key" />
                    </Form.Item>
                  ) : null
                }}
              </Form.Item>

              <Form.Item
                name="body"
                label="请求体（JSON）"
              >
                <TextArea
                  rows={6}
                  placeholder='{"key": "value"}'
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<ApiOutlined />}
                  loading={loading}
                  block
                >
                  发送请求
                </Button>
              </Form.Item>
            </Col>

            <Col xs={24} md={12}>
              <Divider orientation="left">📊 响应结果</Divider>
              {result ? (
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <strong>状态码：</strong>
                      <Tag color={result.status >= 200 && result.status < 300 ? 'success' : 'error'}>
                        {result.status} {result.statusText}
                      </Tag>
                    </div>
                    <div>
                      <strong>响应数据：</strong>
                      <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, maxHeight: 300, overflow: 'auto' }}>
                        {JSON.stringify(result.data, null, 2)}
                      </pre>
                    </div>
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
                    <ApiOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <p>响应结果将在这里显示</p>
                  </div>
                </Card>
              )}
            </Col>
          </Row>
        </Form>

        <Divider orientation="left">📋 请求历史</Divider>
        <Table
          columns={columns}
          dataSource={history}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 5 }}
        />
      </Card>
    </div>
  )
}

export default HTTPIntegration