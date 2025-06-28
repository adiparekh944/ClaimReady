'use client';

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import '@/app/globals.css';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <Navbar />
      
      <main className="pt-10 pb-20">
        {/* Hero Section - White */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="container mx-auto px-4 mb-0 py-20 bg-[var(--color-bg-primary)]"
        >
          <div className="flex flex-col md:flex-row items-center">
            <div className="md:w-1/2 mb-10 md:mb-0 md:pr-10">
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-kumbh-sans text-white mb-6 leading-tight">
                Insure with Confidence.
              </h1>
              <p className="text-xl mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)]">
              ClaimReady uses cutting-edge AI to help homeowners scan their belongings, obtain their value, allowing you to protect what matters most, giving you peace of mind when it counts.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link 
                  href="/upload" 
                  className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                  hover:-translate-y-1
                  shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)] font-kumbh-sans"
                >
                  Try It Now
                </Link>
              </div>
            </div>
            <div className="md:w-1/2 relative">
              <div className="bg-[var(--color-bg-primary)] rounded-xl overflow-hidden p-4">
                <Image 
                  src="/hompage_pic.png"
                  alt="Modern living room" 
                  width={2000}
                  height={1330}
                  className="w-full h-[500px] md:h-[600px] object-cover rounded-lg"
                />
              </div>
              
              {/*<div className="absolute -bottom-6 -right-6 bg-black rounded-lg p-4 shadow-lg">
                <p className="text-sm font-bold text-white">Protect your home with confidence</p>
              </div>*/}
            </div>
          </div>
        </motion.div>

        {/* How It Works Section - White */}
        <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-8 text-center font-black-future">How It Works</h2>
            <div className="max-w-3xl mx-auto space-y-8 mb-8">
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">1</div>
                <div>
                  <h3 className="font-kumbh-sans text-[var(--color-text-primary)] text-lg">Take pictures of your home</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Simply obtain pictures of your home, capturing your belongings.</p>
                </div>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">2</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">Upload to ClaimReady</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Upload your pictures to our AI model.</p>
                </div>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">3</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">AI Analysis</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Our powerful AI scans your photos, recognizes your belongings, and quickly provides value estimates.</p>
                </div>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">4</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">Get Your Estimates</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Receive a detailed table output with item descriptions, images, and estimated values, exportable to CSV format.</p>
                </div>
              </motion.div>
            </div>
          </div>
        </div>

        {/* Features Section - Black */}
        <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-4xl font-bold text-center mb-10 text-[var(--color-text-primary)] font-black-future">The Technology</h2>
            
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
                  className="bg-[var(--color-bg-secondary)] p-6 rounded-xl"
                >
                  <h3 className="text-[var(--color-primary-darktext)] font-bold mb-3 font-kumbh-sans">Object Detection</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans">Accurately detects and recognizes items within your pictures.</p>
                </motion.div>
                
                {/*<motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                  viewport={{ once: true }}
                  className="bg-[var(--color-bg-secondary)] p-6 rounded-xl"
                >
                  <h3 className="text-[var(--color-primary-darktext)] font-bold mb-3">Advanced Tracking</h3>
                  <p className="text-[var(--color-text-dark)]">Sophisticated algorithms to follow items across video frames</p>
                </motion.div>*/}
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="bg-[var(--color-bg-secondary)] p-6 rounded-xl"
                >
                  <h3 className="text-[var(--color-primary-darktext)] font-bold mb-3 font-kumbh-sans">AI Value Estimation</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans">Obtains an accurate valuation of your belongings</p>
                </motion.div>
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="bg-[var(--color-bg-secondary)] p-6 rounded-xl"
                >
                  <h3 className="text-[var(--color-primary-darktext)] font-bold mb-3 font-kumbh-sans">Protected Cloud Storage</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans">Your valuation data is securely stored and easy to access</p>
                </motion.div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer - Black */}
      <footer className="bg-black text-[var(--color-primary)] py-10">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-6 md:mb-0">
              <h3 className="text-2xl font-bold font-black-future">ClaimReady</h3>
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