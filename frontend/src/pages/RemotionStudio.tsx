import React, { useState } from 'react'
import { Card, Tabs, Row, Col, message } from 'antd'
import { VideoCameraOutlined, SettingOutlined } from '@ant-design/icons'
import { Player } from '@remotion/player'
import MyVideo from '../remotion/MyVideo'
import EffectSelector from '../components/RemotionEffects/EffectSelector'
import EffectConfig from '../components/RemotionEffects/EffectConfig'
import EffectRender from '../components/RemotionEffects/EffectRender'

const { TabPane } = Tabs

const RemotionStudio: React.FC = () => {
  const [selectedProject, setSelectedProject] = useState<any>()
  const [renderParams, setRenderParams] = useState<Record<string, any>>({})

  const handleProjectSelect = (project: any) => {
    setSelectedProject(project)
    message.success(`已选择特效: ${project.name}`)
  }

  const handleParamsChange = (params: Record<string, any>) => {
    setRenderParams(params)
  }

  return (
    <div>
      <Card title="Remotion 工作室" extra={<VideoCameraOutlined />}>
        <Tabs defaultActiveKey="effects">
          <TabPane tab="特效视频" key="effects">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <EffectSelector
                  onSelect={handleProjectSelect}
                  selectedProjectId={selectedProject?.id}
                />
              </Col>
              <Col xs={24} lg={8}>
                <EffectConfig
                  projectId={selectedProject?.id}
                  onChange={handleParamsChange}
                />
              </Col>
              <Col xs={24} lg={8}>
                <EffectRender
                  projectId={selectedProject?.id}
                  params={renderParams}
                />
              </Col>
            </Row>
          </TabPane>
          
          <TabPane tab="基础视频" key="basic">
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="视频配置" extra={<SettingOutlined />}>
                  <div style={{ padding: 20, textAlign: 'center', color: '#999' }}>
                    基础视频配置功能
                  </div>
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="视频预览">
                  <div style={{ width: '100%', aspectRatio: '16/9', background: '#000' }}>
                    <Player
                      component={MyVideo}
                      inputProps={{
                        title: '示例视频',
                        description: '这是一个使用 Remotion 创建的视频示例',
                      }}
                      durationInFrames={300}
                      compositionWidth={1920}
                      compositionHeight={1080}
                      fps={30}
                      controls
                      style={{ width: '100%', height: '100%' }}
                    />
                  </div>
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default RemotionStudio