import React from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import {
  VideoCameraOutlined,
  FileTextOutlined,
  CloudUploadOutlined,
  MailOutlined,
} from '@ant-design/icons'

const Dashboard: React.FC = () => {
  return (
    <div>
      <h2>仪表盘</h2>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="视频处理"
              value={0}
              prefix={<VideoCameraOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="模板数量"
              value={0}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="文件上传"
              value={0}
              prefix={<CloudUploadOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="邮件发送"
              value={0}
              prefix={<MailOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="欢迎使用 VD 视频处理服务"
        style={{ marginTop: 16 }}
      >
        <p>这是一个基于 React + FastAPI + Remotion 的现代化视频处理平台。</p>
        <p>功能特性：</p>
        <ul>
          <li>🎤 语音合成 - 基于 VoxCPM 的高质量语音合成</li>
          <li>📝 字幕生成 - 自动生成视频字幕，支持翻译和烧录</li>
          <li>🖼️ 图像处理 - 图片去背景、图片混合等图像处理功能</li>
          <li>🎬 视频转场 - 多种专业视频转场效果</li>
          <li>🔗 视频合并 - 合并多个视频文件为一个视频</li>
          <li>🎨 Remotion工作室 - 自动化视频处理和渲染</li>
        </ul>
      </Card>
    </div>
  )
}

export default Dashboard