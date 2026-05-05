import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import MainLayout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import TemplateManager from './pages/TemplateManager'
import EmailSender from './pages/EmailSender'
import FilePersistence from './pages/FilePersistence'
import RemotionStudio from './pages/RemotionStudio'
import TTSSynthesis from './pages/TTSSynthesis'
import SubtitleGeneration from './pages/SubtitleGeneration'
import ImageProcessing from './pages/ImageProcessing'
import VideoEditor from './pages/VideoEditor'
import VideoTransition from './pages/VideoTransition'
import VideoMerge from './pages/VideoMerge'
import BatchProcessing from './pages/BatchProcessing'
import ComfyUIIntegration from './pages/ComfyUIIntegration'
import HTTPIntegration from './pages/HTTPIntegration'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          isAuthenticated ? (
            <MainLayout>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/tts" element={<TTSSynthesis />} />
                <Route path="/subtitle" element={<SubtitleGeneration />} />
                <Route path="/image" element={<ImageProcessing />} />
                <Route path="/video-editor" element={<VideoEditor />} />
                <Route path="/video-transition" element={<VideoTransition />} />
                <Route path="/video-merge" element={<VideoMerge />} />
                <Route path="/batch" element={<BatchProcessing />} />
                <Route path="/templates" element={<TemplateManager />} />
                <Route path="/email" element={<EmailSender />} />
                <Route path="/files" element={<FilePersistence />} />
                <Route path="/comfyui" element={<ComfyUIIntegration />} />
                <Route path="/http" element={<HTTPIntegration />} />
                <Route path="/remotion" element={<RemotionStudio />} />
              </Routes>
            </MainLayout>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  )
}

export default App