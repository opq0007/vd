import React, { useState, useEffect } from 'react'
import { Card, Select, message, Spin } from 'antd'
import { AppstoreOutlined } from '@ant-design/icons'
import { remotionApi } from '../../services/remotionApi'

const { Option } = Select

interface EffectSelectorProps {
  onSelect?: (project: any) => void
  selectedProjectId?: string
}

const EffectSelector: React.FC<EffectSelectorProps> = ({
  onSelect,
  selectedProjectId,
}) => {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await remotionApi.getProjects()
      setProjects(data)
    } catch (error) {
      message.error('加载特效列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (projectId: string) => {
    const project = projects.find((p) => p.id === projectId)
    if (project && onSelect) {
      onSelect(project)
    }
  }

  return (
    <Card title="选择特效" extra={<AppstoreOutlined />}>
      <Spin spinning={loading}>
        <Select
          style={{ width: '100%' }}
          placeholder="请选择特效"
          value={selectedProjectId}
          onChange={handleSelect}
          size="large"
        >
          {projects.map((project) => (
            <Option key={project.id} value={project.id}>
              {project.name}
            </Option>
          ))}
        </Select>
      </Spin>
    </Card>
  )
}

export default EffectSelector