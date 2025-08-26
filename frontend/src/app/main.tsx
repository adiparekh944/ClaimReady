'use client';

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";

import '@/app/globals.css';
import { MdLinkedCamera, MdFileUpload } from "react-icons/md";
import {FaInnosoft} from "react-icons/fa"
import { FaRegObjectGroup, FaFileInvoiceDollar, FaShieldHalved } from "react-icons/fa6";
import posthog from '../lib/posthog'; 


export default function AboutPage() {
  useEffect(() => {
    posthog.capture('$pageview', { page: 'MainPage' });
  }, []);
  // Add state to detect mobile
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Only run on client
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize(); // set on mount
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <div className="relative min-h-screen bg-[var(--color-bg-primary)]">
      <Navbar />
      <main className="pt-10 pb-20 relative">
  
        {/* Hero Section - White */}
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

        {/* How It Works Section - White */}
        <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-8 text-center font-clash-display-semibold">How It Works</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                viewport={{ once: true }}
                className="p-6 rounded-[20px]"
                style={{
                  backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                }}
              >
                  <MdLinkedCamera size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                 <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">Take pictures of your home</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Simply obtain pictures of your home, capturing your belongings.</p>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                viewport={{ once: true }}
                className="p-6 rounded-[20px]"
                style={{
                  backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                }}
                >
                   
                  <MdFileUpload size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                 <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">Upload to ClaimReady</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Upload your pictures to our AI model.</p>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                viewport={{ once: true }}
                className="p-6 rounded-[20px]"
                style={{
                  backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                }}
              >
                <FaInnosoft size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">AI Analysis</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Our powerful AI scans your photos, recognizes your belongings, and quickly provides value estimates.</p>
              </motion.div>
              
              {/*<motion.div 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="p-6 rounded-[20px]"
                style={{
                  backgroundColor: 'rgb(245, 245, 245)',
                  boxShadow: 'rgba(255, 255, 255, 0.15) 0px 0.706592px 0.706592px -0.666667px, rgba(255, 255, 255, 0.15) 0px 1.80656px 1.80656px -1.33333px, rgba(255, 255, 255, 0.12) 0px 3.62176px 3.62176px -2px, rgba(255, 255, 255, 0.12) 0px 6.8656px 6.8656px -2.66667px, rgba(255, 255, 255, 0.08) 0px 13.6468px 13.6468px -3.33333px, rgba(255, 255, 255, 0.04) 0px 30px 30px -4px, rgb(255, 255, 255) 0px 3px 1px 0px inset'
                }}
              >
                <h3 className="font-kumbh-sans text-[var(--color-primary-darktext)] text-lg font-bold mb-3">Get Your Estimates</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-sm">Receive a detailed table output with item descriptions, images, and estimated values, exportable to CSV format.</p>
              </motion.div> */}
            </div>
          </div>
        </div>

        {/* Features Section - Black */}
        <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-center mb-10 text-[var(--color-text-primary)] font-clash-display-semibold">The Technology</h2>
            
            <div className="max-w-5xl mx-auto text-[var(--color-text-primary)] mb-10">
              <p className="text-[var(--color-text-secondary)] mb-7 text-center font-kumbh-sans">
                ClaimReady leverages advanced computer vision <br />and machine learning technologies to deliver fast, accurate results.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px]"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                  }}
                >
                                     <FaRegObjectGroup size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                   <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Object Detection</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Accurately detects and recognizes items within your pictures.</p>
                </motion.div>
                
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px]"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                  }}
                >
                  <FaFileInvoiceDollar size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">AI Value Estimation</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Obtains an accurate valuation of your belongings.</p>
                </motion.div>
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px]"
                  style={{
                  backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                  borderRadius: '20px',
                  height: '100%',
                  width: '100%',
                  boxShadow: `
                    rgba(0, 0, 0, 0.08) 0px 1px 2px,
                    rgba(0, 0, 0, 0.08) 0px 2px 4px,
                    rgba(0, 0, 0, 0.07) 0px 4px 8px,
                    rgba(0, 0, 0, 0.07) 0px 8px 16px,
                    rgba(0, 0, 0, 0.06) 0px 16px 32px,
                    rgba(0, 0, 0, 0.05) 0px 32px 64px
                  `
                  }}
                >
                  <FaShieldHalved size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Protected Cloud Storage</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Your valuation data is securely stored and easy to access.</p>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer - Black */}
      <footer className="bg-[var(--color-bg-primary)] text-[var(--color-primary)] py-10">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-6 md:mb-0">
              <h3 className="text-2xl font-bold font-clash-display-semibold">ClaimReady</h3>
              <p className="font-kumbh-sans text-[var(--color-text-secondary)]">Scan. Value. Protect.</p>
            </div>
          </div>
          <div className="mt-8 pt-8 font-kumbh-sans border-t border-[var(--color-text-secondary)] text-center text-[var(--color-text-secondary)]">
            <div className="flex flex-col md:flex-row justify-center items-center space-y-2 md:space-y-0 md:space-x-6 mb-4">
              <Link href="/privacy-policy" className="hover:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors">
                Privacy Policy
              </Link>
              <Link href="/terms-of-service" className="hover:text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors">
                Terms of Service
              </Link>
            </div>
            <p>ClaimReady. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}