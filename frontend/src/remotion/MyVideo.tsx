import React from 'react'
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Sequence } from 'remotion'

interface MyVideoProps {
  title: string
  description: string
}

const MyVideo: React.FC<MyVideoProps> = ({ title, description }) => {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()

  const opacity = interpolate(
    frame,
    [0, 30],
    [0, 1],
    { extrapolateRight: 'clamp' }
  )

  const scale = interpolate(
    frame,
    [0, durationInFrames],
    [0.8, 1],
    { extrapolateRight: 'clamp' }
  )

  return (
    <AbsoluteFill style={{ backgroundColor: '#1a1a1a' }}>
      <Sequence from={0}>
        <AbsoluteFill
          style={{
            justifyContent: 'center',
            alignItems: 'center',
            opacity,
            transform: `scale(${scale})`,
          }}
        >
          <div
            style={{
              textAlign: 'center',
              color: 'white',
              padding: 40,
            }}
          >
            <div
              style={{
                fontSize: 80,
                fontWeight: 'bold',
                marginBottom: 20,
              }}
            >
              {title || '示例视频'}
            </div>
            <div
              style={{
                fontSize: 32,
                opacity: 0.8,
              }}
            >
              {description || '这是一个使用 Remotion 创建的视频示例'}
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  )
}

export default MyVideo