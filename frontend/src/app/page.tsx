'use client';

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import '@/app/globals.css';
import { MdLinkedCamera, MdFileUpload } from "react-icons/md";
import { FaInnosoft } from "react-icons/fa";
import { FaRegObjectGroup, FaFileInvoiceDollar, FaShieldHalved } from "react-icons/fa6";
import posthog from '../lib/posthog';

export default function AboutPage() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <div className="relative min-h-screen bg-[var(--color-bg-primary)]">
      <Navbar />
      <main className="pt-10 pb-20 relative z-10">
        <div className="flex flex-col md:flex-row items-center px-4 md:px-10">
          <div className="md:w-1/2 mb-4 md:mb-0 md:pr-10 flex flex-col items-center md:items-start">
            <h1 className="text-5xl lg:text-7xl font-kumbh-sans text-[var(--color-text-primary)] leading-tight text-center md:text-left">
              Claim with
            </h1>
            <h1 className="text-5xl lg:text-7xl font-kumbh-sans text-[var(--color-primary)] mb-6 leading-tight text-center md:text-left">
              Confidence
            </h1>
            <p className="text-xl mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)] text-center md:text-left">
              ClaimReady uses cutting-edge AI to help homeowners scan their belongings, obtain their value, allowing you to protect what matters most, giving you peace of mind when it counts.
            </p>
            <div className="flex flex-wrap gap-4 justify-center md:justify-start">
              <Link 
                href="/upload" 
                className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                hover:-translate-y-1
                shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)] font-kumbh-sans"
                onClick={() => posthog.capture('try_it_now_clicked')}
              >
                Try It Now
              </Link>
            </div>
          </div>
          <div className="md:w-1/2 w-full flex justify-center md:justify-end mt-8 md:mt-0">
            <div className="rounded-xl overflow-hidden p-4 md:p-4 pt-0 md:pt-4 w-full max-w-[500px]">
              <Image 
                src="/home_pic.png"
                alt="Modern living room" 
                width={500}
                height={500}
                className="w-full h-[320px] md:h-[580px] object-contain rounded-lg"
              />
            </div>
          </div>
        </div>
        {/* ...rest of the original content... */}
      </main>
      <footer className="bg-[var(--color-bg-primary)] text-[var(--color-primary)] py-10">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-6 md:mb-0">
              <h3 className="text-2xl font-bold font-clash-display-semibold">ClaimReady</h3>
              <p className="font-kumbh-sans text-[var(--color-text-secondary)]">Scan. Value. Protect.</p>
            </div>
          </div>
          <div className="mt-8 pt-8 font-kumbh-sans border-t border-[var(--color-text-secondary)] text-center text-[var(--color-text-secondary)]">
            <p>ClaimReady. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
} 