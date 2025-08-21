'use client';

import Spline from '@splinetool/react-spline';

export default function SplineScene() {
  return (
    <div className="relative w-full h-[60vh] md:h-[80vh]">
      <Spline
        scene="https://prod.spline.design/9JjeFS0KGfyPoCWp/scene.splinecode"
        className="absolute inset-0"
      />
    </div>
  );
}