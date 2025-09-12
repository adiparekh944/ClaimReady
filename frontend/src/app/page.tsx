'use client';

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import '@/app/globals.css';
import {FaShieldHalved, FaFileExport } from "react-icons/fa6";
import { FaHome } from "react-icons/fa";
import posthog from '../lib/posthog';
import { useEffect, useState, useRef } from "react";
import { MdLinkedCamera, MdFileUpload, MdRealEstateAgent } from "react-icons/md";
import {FaInnosoft} from "react-icons/fa"
import { RiAccountCircle2Fill } from "react-icons/ri";
import { IoPeopleSharp } from "react-icons/io5";
import { TiArrowRightThick } from "react-icons/ti";
import { TextShimmer } from "../../components/motion-primitives/text-shimmer";
import { BackgroundGradient } from "@/components/ui/background-gradient";
import LunarStickyScroll from "@/components/LunarStickyScroll";
import { BackgroundBeams } from "@/components/ui/background-beams";

import { BorderBeam } from "@/components/magicui/border-beam";


export default function AboutPage() {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [isMobile, setIsMobile] = useState(false);
  const [showArrow, setShowArrow] = useState(true);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    const onScroll = () => {
      console.log('window.scrollY:', window.scrollY);
      setShowArrow(window.scrollY < 200); // Show arrow until user scrolls 200px down
    };
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  
  return (
    <div className="relative min-h-screen bg-[var(--color-bg-dark)]">
      <Navbar />
      <main className="relative z-10 bg-[var(--color-bg-dark)]">
        
        {/* MVP Banner - centered for the whole hero section */}
        <div className="flex justify-center w-full mb-6">
          <span className="px-4 py-1 rounded-full bg-[var(--color-primary)] bg-opacity-10 text-white font-semibold font-kumbh-sans text-sm shadow-md border border-[var(--color-primary)]">ClaimReady is in beta development</span>
        </div>
        <div className="relative isolate overflow-hidden flex flex-col md:flex-row items-center justify-center min-h-screen mb-16 px-4 md:px-10">
          <BackgroundBeams/>
              
          {/* Left: Claim with Confidence */}
          
          <div className="relative z-10 md:w-3/5 flex flex-col items-start justify-center mb-8 md:mb-0 md:pr-10">
            <div className="relative inline-block">
            
              <div className="pointer-events-none absolute -inset-2 z-0">
              </div>
              <h1 className="relative z-10 text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-clash-display-semibold leading-tight text-left text-[var(--color-text-primary)] break-words text-balance">
                Your Home Inventory,{" "}
                <TextShimmer
                  duration={5}
                  className="inline-block [--base-color:var(--color-blue-600)] [--base-gradient-color:var(--color-blue-200)] dark:[--base-color:var(--color-blue-700)] dark:[--base-gradient-color:var(--color-blue-400)]"
                >
                  Automated
                </TextShimmer>
              </h1>
            </div>
            <p className="text-xl mt-6 mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)] text-left">
            Ditch manual spreadsheets and endless paperwork. ClaimReady automates your home inventory and creates bulletproof insurance claims, ensuring your belongings are fully valued and your payout is maximized.
            </p>
        
            
            <div className="flex flex-wrap gap-4 justify-start">

                <Link 
                  href="/upload" 
                  className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                  hover:-translate-y-1
                  shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_white] font-kumbh-sans text-center flex items-center gap-2 relative overflow-hidden"
                  onClick={() => posthog.capture('try_it_now_clicked')}
                >
                  Try It Now
                  <TiArrowRightThick className="inline-block pb-1" size={25} />
                  <span className="pointer-events-none  inset-0 rounded-[1.15rem]">
                    <BorderBeam duration={2} size={50} borderWidth={3} colorFrom="white" colorTo="white"/>
                  </span>
                </Link>
            </div>
          </div>

          
          {/* Right: Image */}
          <div className="relative z-10 md:w-2/5 w-full flex justify-center md:justify-end mt-8 md:mt-0">
            <div className="rounded-xl overflow-hidden p-4 md:p-4 pt-0 md:pt-4 w-full max-w-[500px]">
              <Image 
                src="/home_pic.png"
                alt="ClaimReady" 
                width={600}
                height={600}
                className="w-full h-[320px] md:h-[580px] object-contain rounded-lg"
              />
            </div>
          </div>
        </div>
        {/* stats section - White */}
        <div className="bg-[var(--color-bg-dark)]">
          <div className="container mx-auto px-4 mb-20">
            <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-20 text-center font-clash-display-semibold">Every Year, Natural Disasters Ravage America</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              <BackgroundGradient className="rounded-[20px]">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] bg"
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

                    <FaHome size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                   <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">10% of Homes</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">1 in 10 homes are affected by <br/>natural disasters.</p>
                </motion.div>
              </BackgroundGradient>
              <BackgroundGradient className="rounded-[20px]">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px]"
                  style={{
                    backgroundColor: 'rgb(255, 255, 255)', // unified with first card
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
                  <IoPeopleSharp size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                  <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">41% of People</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">41% of Americans live in <br/>diaster-declared zones.</p>
                </motion.div>
              </BackgroundGradient>
              <BackgroundGradient className="rounded-[20px]">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px]"
                  style={{
                    backgroundColor: 'rgb(255, 255, 255)', // unified with first card
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
                     
                    <MdRealEstateAgent size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                   <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">6 Million Property Insurance Claims</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Over 6 million property insurance claims are filed per year.</p>
                </motion.div>
              </BackgroundGradient>
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

        {/* Disaster Showcase Cards Section */}
        <div className="container mx-auto px-4 mb-15">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            {/* Card 1: Flood Damage */}
            <div className="bg-[var-(-color-bg-dark)] rounded-xl shadow-2xl drop-shadow-lg overflow-hidden transition-transform duration-500 hover:-rotate-1 hover:scale-105 cursor-pointer flex flex-col items-center w-full max-w-2xl mx-auto">
              <div className="rounded-xl overflow-hidden w-full">
                <Image 
                  src="/texasflood.png"
                  alt="Flood damage"
                  width={1200}
                  height={800}
                  className="w-full aspect-[3/2] md:aspect-[16/9] rounded-lg object-cover"
                />
                <p className="px-4 py-3 text-sm text-white font-kumbh-sans text-center">Texas Floods, July 2025</p>
              </div>
            </div>
            {/* Card 2: Placeholder for future image */}
            <div className="bg-[var-(-color-bg-dark)] rounded-xl shadow-2xl drop-shadow-lg overflow-hidden transition-transform duration-500 hover:rotate-1 hover:scale-105 cursor-pointer flex flex-col items-center w-full max-w-2xl mx-auto">
              <div className="rounded-xl overflow-hidden w-full">
                <Image 
                  src="/lafire.png"
                  alt="Fire damage"
                  width={1200}
                  height={800}
                  className="w-full aspect-[3/2] md:aspect-[16/9] rounded-lg object-cover"
                />
                <p className="px-4 py-3 text-sm text-white font-kumbh-sans text-center">LA Wildfires, January 2025</p>
              </div>
            </div>
          </div>
        </div>
                
        {/* Commented out old StickyScroll - kept for reference */}
        {/* <div className="w-full mt-50 mb-40 bg-[var(--color-bg-dark)]">
            <StickyScroll content={content} />
        </div> */}
        
        {/* New LunarStickyScroll implementation */}
        <div className="w-full mt-40">
          <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-20 text-center font-clash-display-semibold"> 
            The Current Claims Process
          </h2>
        </div>
        <div className="w-full bg-[var(--color-bg-dark)]">
            <LunarStickyScroll />
        </div>
                


        {/* How It Works Section - White */}
        <div className="bg-[var(--color-bg-dark)]">
          <div className="container mx-auto px-4 mt-15">
            <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-8 text-center font-clash-display-semibold">Enter ClaimReady</h2>
            <p className="text-xl mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)] text-center ">
             With ClaimReady, we handle steps 2-6 of the current process, saving time and effort. 
            </p>
            <div className="grid items-stretch grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              <BackgroundGradient className="rounded-[20px] h-full">
              <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] h-full flex flex-col"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                    borderRadius: '20px',
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
              </BackgroundGradient>
              
              <BackgroundGradient className="rounded-[20px] h-full">
                 <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] h-full flex flex-col"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                    borderRadius: '20px',
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
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Upload your pictures on our AI model.</p>
                </motion.div>
              </BackgroundGradient>
              
              <BackgroundGradient className="rounded-[20px] h-full">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] h-full flex flex-col"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                    borderRadius: '20px',
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
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Our powerful AI scans your photos, recognizes your belongings, and quickly obtains an accurate valuation.</p>
                </motion.div>
              </BackgroundGradient>
              
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
        <div className="py-20 bg-[var(--color-bg-dark)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-center mb-10 mt-35 text-[var(--color-text-primary)] font-clash-display-semibold">What Makes ClaimReady Even Better</h2>
            
            <div className="max-w-5xl mx-auto text-[var(--color-text-primary)] mb-10">
              <p className="text-[var(--color-text-secondary)] mb-7 text-center font-kumbh-sans text-xl">
                ClaimReady has these additional features to make <br/> filing your claim to insurance even faster and easier.
              </p>
              
              <div className="grid items-stretch grid-cols-1 md:grid-cols-3 gap-6">
                <BackgroundGradient className="rounded-[20px] h-full">
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    viewport={{ once: true }}
                    className="p-6 rounded-[20px] h-full flex flex-col"
                    style={{
                      backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                      borderRadius: '20px',
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
                    <FaFileExport size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                    <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Export to CSV</h3>
                    <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">We export your valuation to a CSV format, allowing you to directly submit it to your insurance.</p>
                  </motion.div>
                </BackgroundGradient>
                <BackgroundGradient className="rounded-[20px] h-full">
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    viewport={{ once: true }}
                    className="p-6 rounded-[20px] h-full flex flex-col"
                    style={{
                      backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                      borderRadius: '20px',
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
                    <RiAccountCircle2Fill size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                    <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Saved Account Info</h3>
                    <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Never fear of losing your valuations with saved account information.</p>
                  </motion.div>
                </BackgroundGradient>
                <BackgroundGradient className="rounded-[20px] h-full">
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                    viewport={{ once: true }}
                    className="p-6 rounded-[20px] h-full flex flex-col"
                    style={{
                      backgroundColor: 'rgb(245, 245, 245)', // matches screenshot
                      borderRadius: '20px',
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
                </BackgroundGradient>
              </div>
            </div>
            {/* Try It Now Button at the bottom */}

            <div className="flex flex-wrap gap-4 justify-center">
                <Link 
                  href="/upload" 
                  className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                  hover:-translate-y-1
                  shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_white] font-kumbh-sans text-center flex items-center gap-2 relative overflow-hidden"
                  onClick={() => posthog.capture('try_it_now_clicked')}
                >
                  Try It Now
                  <TiArrowRightThick className="inline-block pb-1" size={25} />
                  <span className="pointer-events-none  inset-0 rounded-[1.15rem]">
                    <BorderBeam duration={2} size={50} borderWidth={3} colorFrom="white" colorTo="white"/>
                  </span>
                </Link>
            </div>
          </div>
        </div>

        {/* Features Section - Black */}
        <div className="py-20 bg-[var(--color-bg-dark)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-center mb-10 text-[var(--color-text-primary)] font-clash-display-semibold">Meet the Team</h2>  
              {/* Team member images commented out due to missing files */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] max-w-sm w-full mx-auto"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)',
                    borderRadius: '20px',
                    height: '100%',
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
                  <Image 
                  src="/adi.jpeg"
                  alt="Aditya Parekh"
                  width={80}
                  height={80}
                  className= "w-24 h-24 rounded-full object-cover mx-auto mb-4 shadow"
                />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Aditya Parekh
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Science & Data Science<br/>University of Wisconsin-Madison
                  </p>
                </motion.div>
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] max-w-sm w-full mx-auto"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)',
                    borderRadius: '20px',
                    height: '100%',
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
                <Image 
                  src="/smyan.jpeg"
                  alt="Smyan Vinu"
                  width={80}
                  height={80}
                  className= "w-24 h-24 rounded-full object-cover mx-auto mb-4 shadow"
                />
                <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Smyan Vinu
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Science, Data Science & Statistics<br/>University of Wisconsin-Madison
                  </p>
                </motion.div>
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] max-w-sm w-full mx-auto"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)',
                    borderRadius: '20px',
                    height: '100%',
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
                  <Image 
                    src="/arnav.png"
                    alt="Arnav Mohanty"
                    width={80}
                    height={80}
                    className= "w-24 h-24 rounded-full object-cover mx-auto mb-4 shadow"
                  />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Arnav Mohanty
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Engineering & Computer Science <br/>University of Wisconsin-Madison
                  </p>
                </motion.div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-6 justify-items-center">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] max-w-sm w-full mx-auto"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)',
                    borderRadius: '20px',
                    height: '100%',
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
                  <Image 
                    src="/soham.jpeg"
                    alt="Soham Kundu"
                    width={80}
                    height={80}
                    className= "w-24 h-24 rounded-full object-cover mx-auto mb-4 shadow"
                  />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Soham Kundu
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Engineering & Computer Science <br/>University of Wisconsin-Madison
                  </p>
                </motion.div>

                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-[20px] max-w-sm w-full mx-auto"
                  style={{
                    backgroundColor: 'rgb(245, 245, 245)',
                    borderRadius: '20px',
                    height: '100%',
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
                  <Image 
                    src="/jayanth.jpeg"
                    alt="Jayanth Balu"
                    width={80}
                    height={80}
                    className= "w-24 h-24 rounded-full object-cover mx-auto mb-4 shadow"
                  />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Jayanth Balu
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Science & Statistics <br/>University of Wisconsin-Madison
                  </p>
                </motion.div>
              </div>
          </div>
        </div>
        <style jsx global>{`
          @keyframes shimmer {
            0% { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
          }
          .shimmer-text {
            animation: shimmer 2.5s linear infinite;
          }
        `}</style>
      </main>
      <footer className="bg-[var(--color-bg-dark)] text-[var(--color-primary)] py-10">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-6 md:mb-0">
              <h3 className="text-2xl font-bold font-clash-display-semibold">ClaimReady</h3>
              <p className="font-kumbh-sans text-[var(--color-text-secondary)]">Scan. Value. Protect.</p>
            </div>
          </div>
          <div className="mt-8 pt-8 font-kumbh-sans border-t border-[var(--color-text-secondary)] text-center text-[var(--color-text-secondary)]">
            <div className="flex flex-col md:flex-row justify-center items-center space-y-2 md:space-y-0 md:space-x-6 mb-4">
              <Link href="/privacy-policy" className="hover:text-[var(--color-primary)] transition-colors">
                Privacy Policy
              </Link>
              <Link href="/terms-of-service" className="hover:text-[var(--color-primary)] transition-colors">
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