import React, { useState } from 'react'
import { Form, Input, Button, Card, message, Upload } from 'antd'
import { SendOutlined, UploadOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'

const EmailSender: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [fileList, setFileList] = useState<any[]>([])

  const uploadProps: UploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file)
      const newFileList = fileList.slice()
      newFileList.splice(index, 1)
      setFileList(newFileList)
    },
    beforeUpload: (file) => {
      setFileList([...fileList, file])
      return false
    },
    fileList,
  }

  const onFinish = async (_values: any) => {
    setLoading(true)
    try {
      message.success('邮件发送成功')
      form.resetFields()
      setFileList([])
    } catch (error) {
      message.error('邮件发送失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="邮件发送">
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
      >
        <Form.Item
          label="收件人"
          name="to"
          rules={[
            { required: true, message: '请输入收件人邮箱' },
            { type: 'email', message: '请输入有效的邮箱地址' },
          ]}
        >
          <Input placeholder="请输入收件人邮箱" />
        </Form.Item>

        <Form.Item
          label="主题"
          name="subject"
          rules={[{ required: true, message: '请输入邮件主题' }]}
        >
          <Input placeholder="请输入邮件主题" />
        </Form.Item>

        <Form.Item
          label="正文"
          name="body"
          rules={[{ required: true, message: '请输入邮件正文' }]}
        >
          <Input.TextArea
            rows={8}
            placeholder="请输入邮件正文"
          />
        </Form.Item>

        <Form.Item label="附件">
          <Upload {...uploadProps}>
            <Button icon={<UploadOutlined />}>选择文件</Button>
          </Upload>
        </Form.Item>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SendOutlined />}
            loading={loading}
            block
          >
            发送邮件
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

export default EmailSender