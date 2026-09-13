import React, { useState } from 'react';
import { Video } from 'lucide-react';

interface VideoMonitorProps {
  videoUrl: string;
  isLoading?: boolean;
  error?: string | null;
}

export const VideoMonitor: React.FC<VideoMonitorProps> = ({ videoUrl, isLoading }) => {
  const [videoSrc, setVideoSrc] = useState<string>(videoUrl || '/patrol1_final.mp4');
  const [isFallback, setIsFallback] = useState<boolean>(false);

  React.useEffect(() => {
    if (videoUrl && !isFallback) {
      setVideoSrc(videoUrl);
    }
  }, [videoUrl, isFallback]);

  const handleVideoError = () => {
    if (!isFallback) {
      console.warn('Surveillance video stream unavailable from Render backend. Playing local public fallback video (/patrol1_final.mp4).');
      setIsFallback(true);
      setVideoSrc('/patrol1_final.mp4');
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <Video size={16} /> Thermal Video Monitor
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {isFallback ? 'SOURCE: LOCAL FALLBACK PATROL1 SEQUENCE' : 'SOURCE: PATROL1 SEQUENCE (STREAM)'}
        </span>
      </div>

      <div className="panel-body">
        {isLoading && !videoSrc ? (
          <div className="video-container">
            <div style={{ color: 'var(--accent-cyan)', fontSize: '0.9rem' }}>Loading Video Stream...</div>
          </div>
        ) : (
          <div className="video-wrapper" style={{ position: 'relative', width: '100%', borderRadius: '6px', overflow: 'hidden', backgroundColor: '#000' }}>
            <video
              src={videoSrc}
              controls
              autoPlay
              loop
              muted
              playsInline
              onError={handleVideoError}
              style={{
                width: '100%',
                maxHeight: '400px',
                objectFit: 'contain',
                display: 'block',
                backgroundColor: '#000'
              }}
            />

            {/* Video Overlay Top Badge */}
            <div
              style={{
                position: 'absolute',
                top: '10px',
                left: '10px',
                backgroundColor: 'rgba(11, 15, 23, 0.85)',
                border: '1px solid var(--border-medium)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                color: isFallback ? '#60a5fa' : '#fbbf24',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backdropFilter: 'blur(4px)'
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: isFallback ? '#60a5fa' : '#fbbf24' }}></span>
              <span>{isFallback ? 'LOCAL FALLBACK THERMAL DATA' : 'PRE-RECORDED THERMAL DATA'}</span>
            </div>

            {/* Video Overlay Bottom Bar */}
            <div
              style={{
                position: 'absolute',
                bottom: '40px',
                left: '10px',
                backgroundColor: 'rgba(11, 15, 23, 0.80)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '0.68rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                display: 'flex',
                gap: '12px'
              }}
            >
              <span>FEED: CAM-01</span>
              <span>RES: 1080 × 720</span>
              <span>TYPE: THERMAL IR</span>
              <span>MODE: {isFallback ? 'LOCAL PUBLIC FALLBACK' : 'API RANGE STREAM'}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};


export default VideoMonitor;
