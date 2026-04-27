export interface User {
  username: string
  token: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  success: boolean
  message: string
  token?: string
}

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
  error?: string
}

export interface Template {
  id: string
  name: string
  description: string
  config: Record<string, any>
  created_at: string
  updated_at: string
}

export interface EmailRequest {
  to: string
  subject: string
  body: string
  attachments?: string[]
}

export interface FileUploadResponse {
  success: boolean
  message: string
  file_path?: string
  file_url?: string
}

export interface RemotionProject {
  id: string
  name: string
  composition: string
  duration: number
  fps: number
  width: number
  height: number
  created_at: string
}