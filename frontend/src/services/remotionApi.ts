import axios, { AxiosInstance } from 'axios'

interface RemotionProject {
  id: string
  name: string
  compositionId: string
}

interface RenderJob {
  id: string
  projectId: string
  projectName: string
  status: 'pending' | 'rendering' | 'completed' | 'failed'
  progress: number
  createdAt: string
  completedAt?: string
  error?: string
  downloadUrl?: string
}

class RemotionApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/remotion',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  async getProjects(): Promise<RemotionProject[]> {
    const response = await this.client.get('/projects')
    return response.data
  }

  async getProjectParams(projectId: string): Promise<any> {
    const response = await this.client.get(`/projects/${projectId}/params`)
    return response.data
  }

  async createRenderJob(projectId: string, params: Record<string, any>): Promise<{ success: boolean; jobId: string; message: string }> {
    const response = await this.client.post(`/render/${projectId}`, params)
    return response.data
  }

  async createComposeJob(params: { mergeMode: string; effects: any[] }): Promise<{ success: boolean; jobId: string; message: string }> {
    const response = await this.client.post('/compose', params)
    return response.data
  }

  async getJobStatus(jobId: string): Promise<RenderJob> {
    const response = await this.client.get(`/jobs/${jobId}`)
    return response.data
  }

  async downloadJobOutput(jobId: string): Promise<Blob> {
    const response = await this.client.get(`/download/${jobId}`, {
      responseType: 'blob',
    })
    return response.data
  }
}

export const remotionApi = new RemotionApiClient()