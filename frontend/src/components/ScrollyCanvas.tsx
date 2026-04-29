'use client';

import { useEffect, useRef, useState } from 'react';

interface ScrollyCanvasProps {
  frameIndex: number;
  totalFrames: number;
}

export default function ScrollyCanvas({ frameIndex, totalFrames }: ScrollyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imagesRef = useRef<HTMLImageElement[]>([]);
  const [loadedCount, setLoadedCount] = useState(0);

  // Preload all images
  useEffect(() => {
    const urls = Array.from({ length: totalFrames }, (_, i) => `/frames/frame_${i + 1}.png`);
    
    urls.forEach((url, i) => {
      const img = new Image();
      img.src = url;
      img.onload = () => {
        imagesRef.current[i] = img;
        setLoadedCount((prev) => prev + 1);
      };
    });
  }, [totalFrames]);

  // Draw current frame
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = imagesRef.current[frameIndex - 1];
    if (!img) return;

    // Handle device pixel ratio for sharpness
    const dpr = window.devicePixelRatio || 1;
    const render = () => {
      const { innerWidth: width, innerHeight: height } = window;
      
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      // Cover logic (similar to object-fit: cover)
      const scale = Math.max(width / img.width, height / img.height);
      const x = (width / 2) - (img.width / 2) * scale;
      const y = (height / 2) - (img.height / 2) * scale;
      
      ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
    };

    requestAnimationFrame(render);
  }, [frameIndex]);

  return (
    <div className="fixed inset-0 z-0">
      <canvas ref={canvasRef} className="block h-full w-full" />
      {loadedCount < totalFrames && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black">
          {/* Ambient glow blobs for depth */}
          <div style={{
            position: 'absolute', top: '35%', left: '50%', transform: 'translate(-50%, -50%)',
            width: '480px', height: '480px', borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)',
            filter: 'blur(40px)', pointerEvents: 'none'
          }} />

          {/* Loader card */}
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '28px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: '20px',
            padding: '48px 64px',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
            boxShadow: '0 0 60px rgba(99,102,241,0.15)',
            minWidth: '320px',
            position: 'relative'
          }}>
            {/* Title */}
            <div style={{ textAlign: 'center' }}>
              <p style={{
                color: 'rgba(255,255,255,0.4)', fontSize: '10px',
                letterSpacing: '0.35em', textTransform: 'uppercase', marginBottom: '8px', fontWeight: 500
              }}>
                AI Travel Agent
              </p>
              <h2 style={{
                color: '#ffffff', fontSize: '22px', fontWeight: 800,
                letterSpacing: '-0.02em', margin: 0
              }}>
                Preparing your experience
              </h2>
            </div>

            {/* Progress bar track */}
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{
                height: '6px', width: '100%', background: 'rgba(255,255,255,0.08)',
                borderRadius: '999px', overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${(loadedCount / totalFrames) * 100}%`,
                  background: 'linear-gradient(90deg, #6366f1, #38bdf8)',
                  borderRadius: '999px',
                  transition: 'width 0.3s ease',
                  boxShadow: '0 0 12px rgba(99,102,241,0.8), 0 0 24px rgba(56,189,248,0.4)'
                }} />
              </div>

              {/* Percentage row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <p style={{
                  color: 'rgba(255,255,255,0.5)', fontSize: '11px',
                  letterSpacing: '0.25em', textTransform: 'uppercase', margin: 0, fontWeight: 500
                }}>
                  Loading frames
                </p>
                <p style={{ color: '#ffffff', fontSize: '13px', fontWeight: 700, margin: 0, fontFamily: 'monospace' }}>
                  {Math.round((loadedCount / totalFrames) * 100)}%
                </p>
              </div>
            </div>

            {/* Pulse dots */}
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{
                  width: '6px', height: '6px', borderRadius: '50%',
                  background: i === 0 ? '#6366f1' : i === 1 ? '#818cf8' : '#38bdf8',
                  animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
                  opacity: 0.8
                }} />
              ))}
            </div>
          </div>

          <style>{`
            @keyframes pulse {
              0%, 100% { transform: scale(1); opacity: 0.6; }
              50% { transform: scale(1.5); opacity: 1; }
            }
          `}</style>
        </div>
      )}
    </div>
  );
}
