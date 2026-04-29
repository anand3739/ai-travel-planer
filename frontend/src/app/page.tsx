'use client';

import { useScroll, useTransform, motion, AnimatePresence } from 'framer-motion';
import { useRef, useState, useEffect } from 'react';
import ScrollyCanvas from '@/components/ScrollyCanvas';
import { ArrowRight } from 'lucide-react';

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Map scroll 0-1 to frame 1-192
  const frameIndex = useTransform(scrollYProgress, [0, 1], [1, 192]);
  const [currentFrame, setCurrentFrame] = useState(1);

  useEffect(() => {
    return frameIndex.on('change', (latest) => {
      setCurrentFrame(Math.round(latest));
    });
  }, [frameIndex]);

  // Text overlay variants
  const sectionOpacity1 = useTransform(scrollYProgress, [0, 0.2, 0.4], [0, 1, 0]);
  const sectionOpacity2 = useTransform(scrollYProgress, [0.4, 0.6, 0.8], [0, 1, 0]);
  const sectionOpacity3 = useTransform(scrollYProgress, [0.8, 0.95, 1], [0, 1, 1]);

  return (
    <main ref={containerRef} className="relative h-[600vh] bg-black">
      {/* Sticky Background Canvas */}
      <ScrollyCanvas frameIndex={currentFrame} totalFrames={192} />

      {/* Hero Section */}
      <section className="sticky top-0 h-screen flex items-center justify-center pointer-events-none z-10">
        <motion.div 
          style={{ opacity: useTransform(scrollYProgress, [0, 0.15], [1, 0]) }}
          className="text-center px-6"
        >
          <h1 className="text-white text-6xl md:text-8xl font-black tracking-tighter mb-4 uppercase">
            Travel <span style={{ color: '#222222' }}>Beyond</span>
          </h1>
          <p className="text-white/60 text-lg md:text-xl tracking-widest uppercase">
            The next generation of travel planning
          </p>
          <div className="mt-12 animate-bounce opacity-40">
            <div className="w-0.5 h-12 bg-white mx-auto" />
          </div>
        </motion.div>
      </section>

      {/* Story Marker 1 */}
      <section className="sticky top-0 h-screen flex items-center justify-center pointer-events-none z-10">
        <motion.div style={{ opacity: sectionOpacity1 }} className="max-w-2xl text-center px-6">
          <h2 className="text-white text-4xl md:text-5xl font-bold tracking-tight mb-6">
            Intelligent Discovery
          </h2>
          <p className="text-white/60 text-lg leading-relaxed">
            Our AI engine analyzes millions of data points to find your perfect destination. 
            Tailored to your preferences, budget, and soul.
          </p>
        </motion.div>
      </section>

      {/* Story Marker 2 */}
      <section className="sticky top-0 h-screen flex items-center justify-center pointer-events-none z-10">
        <motion.div style={{ opacity: sectionOpacity2 }} className="max-w-2xl text-center px-6">
          <h2 className="text-white text-4xl md:text-5xl font-bold tracking-tight mb-6">
            Seamless Orchestration
          </h2>
          <p className="text-white/60 text-lg leading-relaxed">
            Flights, hotels, and local experiences—all synthesized into a single, beautiful itinerary.
            Zero friction, maximum adventure.
          </p>
        </motion.div>
      </section>

      {/* Final CTA */}
      <section className="sticky top-0 h-screen flex items-center justify-center pointer-events-none z-20">
        <motion.div style={{ opacity: sectionOpacity3 }} className="text-center px-6 pointer-events-auto">
          <h2 className="text-white text-5xl md:text-7xl font-bold tracking-tighter mb-8 uppercase">
            <span style={{ color: '#222222' }}>Plan</span> your next journey
          </h2>
          <a 
            href="/create" 
            className="inline-flex items-center gap-2 bg-white text-black px-8 py-4 rounded-full font-bold text-lg hover:bg-neutral-200 transition-colors group"
          >
            Get Started
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>
      </section>

      {/* HUD Elements */}
      <div className="fixed bottom-10 left-10 z-30 transition-opacity duration-1000">
        <div className="text-white/20 text-[10px] tracking-[0.3em] font-medium uppercase rotate-180 [writing-mode:vertical-lr]">
          Sequence 192_ASTRO_PROXIMITY
        </div>
      </div>
      
      <div className="fixed top-10 right-10 z-30 flex items-center gap-4">
        <div className="text-right">
          <div className="text-white/40 text-[10px] tracking-widest uppercase mb-1">Status</div>
          <div className="text-white text-xs font-mono">READY_FOR_LAUNCH</div>
        </div>
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
      </div>
    </main>
  );
}
