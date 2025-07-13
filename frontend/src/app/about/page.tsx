"use client"

import Spline from '@splinetool/react-spline';
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useRouter } from "next/navigation";
{/*import { GooeyText } from "@/components/ui/gooey-text-morphing";
import { motion } from "framer-motion";*/}

export default function LandingPage() {
  const router = useRouter();
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  const handleEnter = () => {
    setIsTransitioning(true);
    // Delay navigation to allow for transition animation
    setTimeout(() => {
      router.push("/about");
    }, 500);
  };
  
  return (
    <div className="relative min-h-screen">
      {/* Spline 3D Background */}
      <div className="absolute inset-0 z-0">
        <Spline
          scene="https://prod.spline.design/fRKsRsH5JECymlBc/scene.splinecode" 
        />
      </div>

      
      {/* Gooey Text Animation, currently broken
      <div className="absolute top-1/4 left-0 right-0 z-10 transform -translate-y-1/2">
        <div className="h-[60px] flex items-center justify-center">
          <GooeyText
            texts={[
              "Scan your Assets",
              "Value with Ease",
              "Protect with Confidence"
            ]}
            morphTime={1.5}
            cooldownTime={2}
            className="font-bold"
            textClassName="text-white drop-shadow-md text-xl font-sans opacity-90"
          />
        </div>
      </div> */}
      
      {/* Button to About Page with transition */}
      <div className="absolute bottom-20 left-0 right-0 flex justify-center z-20">
        <Button 
          variant="default" 
          onClick={handleEnter}
          className={`rounded-[1.15rem] px-8 py-6 text-lg font-semibold backdrop-blur-md 
          bg-black hover:[background:var(--gradient-primary)]
          text-white transition-all duration-500 
          hover:-translate-y-1
          shadow-[var(--shadow-primary)] hover:shadow-[var(--shadow-primary-hover)]
          ${isTransitioning ? 'scale-105 opacity-0 translate-y-10' : 'scale-100 opacity-100'}`}
        >
          <span className="opacity-90 group-hover:opacity-100 transition-opacity text-red">
            Enter ClaimReady
          </span>
          <span className="ml-3 opacity-70 group-hover:opacity-100 group-hover:translate-x-1.5 transition-all duration-300">
            →
          </span>
        </Button>
      </div>
    </div>
  );
}
/*function FeatureCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 hover:shadow-md transition-shadow">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
}*/

