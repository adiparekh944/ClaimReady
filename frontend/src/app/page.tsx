'use client';

import Navbar from "@/components/Navbar";
import { motion } from "framer-motion";
import Link from "next/link";
import '@/app/globals.css';
import  Image from "next/image"
import posthog from '../lib/posthog';
import { useEffect, useState, useRef } from "react";
import { MdLinkedCamera, MdFileUpload, MdRealEstateAgent } from "react-icons/md";
import {FaInnosoft} from "react-icons/fa"
import { FaShieldHalved, FaFileExport } from "react-icons/fa6";
import {FaHome} from "react-icons/fa"
import { RiAccountCircle2Fill } from "react-icons/ri";
import { IoPeopleSharp } from "react-icons/io5";
import { FaImages, FaSortAmountDown, FaClipboardList, FaDollarSign, FaCheck, FaFileAlt } from "react-icons/fa";
import { TiArrowRightThick } from "react-icons/ti";
import Jayanth from "/public/jayanth.jpeg"
import Soham from "/public/soham.jpeg"
import Arnav from "/public/arnav.png"
import Adi from "/public/adi.jpeg"
import Smyan from "/public/smyan.jpeg"

{/*const checkpoints = [
  { id: 1, label: "Gather All Your Images", info: "You must gather all of your images of your belongings in your home." },
  { id: 2, label: "Catalog Every Belonging", info: "You must manually catalog each and every belonging by hand which averages to about 500+." },
  { id: 3, label: "Obtain A Valuation", info: "After getting your belongings cataloged, you must scour the web and find prices for each item individually, taking well over 20+ hours." },
  { id: 4, label: "CSV Consolidation", info: "Finally, in order to submit a claim, all of this information must be put into a csv file for insurance." },
];*/}


/*
function Timeline() {
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLDivElement | null)[]>([]);
  const lineContainerRef = useRef<HTMLDivElement | null>(null);
  const [blueLineHeight, setBlueLineHeight] = useState(0);
  const [grayLineStart, setGrayLineStart] = useState(0);
  const [grayLineHeight, setGrayLineHeight] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      let found = false;
      refs.current.forEach((ref, idx) => {
        if (ref) {
          const rect = ref.getBoundingClientRect();
          if (rect.top < window.innerHeight / 2 && rect.bottom > window.innerHeight / 2) {
            setActive(idx);
            found = true;
          }
        }
      });
      // If not found and near bottom, set last as active
      if (!found) {
        if ((window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 10)) {
          setActive(checkpoints.length - 1);
        }
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Calculate gray line start and height (from center of first to bottom of last checkpoint)
  useEffect(() => {
    if (!lineContainerRef.current || !refs.current[0] || !refs.current[checkpoints.length - 1]) return;
    const containerRect = lineContainerRef.current.getBoundingClientRect();
    const firstRect = refs.current[0]?.getBoundingClientRect();
    const lastRect = refs.current[checkpoints.length - 1]?.getBoundingClientRect();
    if (firstRect && lastRect) {
      const firstCenter = (firstRect.top + firstRect.bottom) / 2 - containerRect.top;
      const lastCenter = (lastRect.top + lastRect.bottom) / 2 - containerRect.top;
      const circleRadius = 16; // px, half of 32px (h-8)
      setGrayLineStart(firstCenter);
      setGrayLineHeight(lastCenter + circleRadius - firstCenter);
    }
  }, [refs, lineContainerRef, checkpoints.length]);

  // Calculate blue line height in px to the center of the active checkpoint
  useEffect(() => {
    if (!lineContainerRef.current || !refs.current[0] || !refs.current[active]) return;
    const containerRect = lineContainerRef.current.getBoundingClientRect();
    const firstRect = refs.current[0]?.getBoundingClientRect();
    const activeRect = refs.current[active]?.getBoundingClientRect();
    if (firstRect && activeRect) {
      const firstCenter = (firstRect.top + firstRect.bottom) / 2 - containerRect.top;
      const activeCenter = (activeRect.top + activeRect.bottom) / 2 - containerRect.top;
      setBlueLineHeight(activeCenter - firstCenter);
    }
  }, [active]);

  return (
    <div className="relative flex justify-center items-start py-20">
      {/* Vertical line 
      <div
        ref={lineContainerRef}
        className="absolute left-1/2 transform -translate-x-1/2 w-1 z-0"
        style={{ height: "100%" }}
      >
        {/* Gray line: always connects all checkpoints 
        <div
          className="absolute left-0 w-1 bg-gray-300"
          style={{
            top: grayLineStart,
            height: grayLineHeight,
          }}
        />
        {/* Blue line: overlays gray line up to active checkpoint 
        <div
          className="absolute left-0 w-1 bg-blue-500 z-10 transition-all duration-300"
          style={{
            top: grayLineStart,
            height: blueLineHeight,
          }}
        />
      </div>
      {/* Checkpoints 
      <div className="flex flex-col items-center w-full max-w-4xl z-20">
        {checkpoints.map((cp, idx) => (
          <div
            key={cp.id}
            ref={el => { refs.current[idx] = el; }}
            className="grid grid-cols-3 items-center mb-32 w-full"
            style={{ minHeight: "118px" }}
          >
            {/* Left side (empty) 
            <div></div>
            {/* Center: Number on timeline 
            <div className="flex flex-col items-center">
              <div
                className={`w-10 h-8 rounded-full flex items-center justify-center border-4 ${
                  idx <= active ? "bg-blue-500 border-blue-500 text-white" : "bg-white border-gray-300 text-gray-400"
                } transition-all duration-300`}
              >
                {cp.id}
              </div>
            </div>
            {/* Right side: Text 
            <div className="text-left pl-2">
              {active === idx && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.6 }}
                >
                  <h3 className="text-xl font-bold">{cp.label}</h3>
                  <p className="mt-2 text-blue-600 font-semibold">{cp.info}</p>
                </motion.div>
              )}
            </div>
          </div>
        ))}
      </div>
      
    </div>
  );
}
*/

// Horizontal Timeline Component
function StickyHorizontalTimeline() {
  const checkpoints = [
    { id: 1, label: "Gather All Your Images", info: "You must gather all of your images of your belongings in your home.", icon: FaImages },
    { id: 2, label: "Sort and Organize Images", info: "Before cataloging, you need to sort and organize all images by room or category to ensure nothing is overlooked.", icon: FaSortAmountDown },
    { id: 3, label: "Catalog Every Belonging", info: "You must manually catalog each and every belonging by hand, which averages to 1500+.", icon: FaClipboardList },
    { id: 4, label: "Obtain A Valuation", info: "After getting your belongings cataloged, you must scour the web and find prices for each item individually, taking well over 20+ hours.", icon: FaDollarSign },
    { id: 5, label: "Verify and Cross-Check Data", info: "You will then need to verify each item’s valuation for accuracy and ensure no duplicate or missing entries exist to avoid claim rejections.", icon: FaCheck },
    { id: 6, label: "CSV Consolidation", info: "Finally, in order to submit a claim, all of this information must be put into a csv file for insurance.", icon: FaFileAlt },
  ];
  const [active, setActive] = useState(0);
  const sectionRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      if (!sectionRef.current) return;
      const rect = sectionRef.current.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      const totalScrollable = rect.height - windowHeight;
      const scrolled = Math.min(Math.max(-rect.top, 0), totalScrollable);
      const progress = totalScrollable > 0 ? scrolled / totalScrollable : 0;
      const buffer = 0.08;
      const idx = Math.round((progress - buffer) * (checkpoints.length - 1));
      setActive(Math.min(Math.max(idx, 0), checkpoints.length - 1));
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Calculate blue bar width as a percentage
  const blueWidth = `${((active + 1) / checkpoints.length) * 100}%`;

  return (
    <div ref={sectionRef} className="w-full h-[200vh] relative flex flex-col items-center justify-center bg-[var(--color-bg-primary)] z-10">
      <div ref={timelineRef} className="sticky top-1/2 -translate-y-1/2 w-full max-w-6xl flex flex-col items-center">
        <h2 className="font-bold font-clash-display-semibold text-5xl text-center mb-8">The Current Claims Process</h2>
        {/* Timeline bar */}
        <div className="relative w-full h-2 bg-gray-300 rounded-full">
          <div
            className="absolute h-2 rounded-full transition-all duration-500"
            style={{
              width: blueWidth,
              background: 'linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-dark) 100%)'
            }}
          ></div>
        </div>
        {/* Checkpoints */}
        <div className="flex w-full justify-between mt-4">
          {checkpoints.map((cp, idx) => {
            const Icon = cp.icon;
            return (
              <div key={cp.id} className="flex flex-col items-center w-1/6">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-4 mb-2 text-xl font-bold font-kumbh-sans transition-all duration-300 ${
                    idx <= active
                      ? "bg-[var(--color-primary)] border-[var(--color-primary)] text-white"
                      : "bg-white border-gray-300 text-gray-400"
                  }`}
                >
                 <Icon size={24} />
                </div>
                <div className="text-center text-xl font-kumbh-sans font-semibold">
                  {cp.label}
                </div>
              </div>
            );
          })}
        </div>
        {/* Active checkpoint info */}
        <div className="mt-8 w-full text-center text-xl text-[var(--color-text-secondary)] font-kumbh-sans min-h-[48px]">
          {checkpoints[active]?.info}
        </div>
      </div>
    </div>
  );
}

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
//fofofof
  return (
    <div className="relative min-h-screen bg-[var(--color-bg-primary)]">
      <Navbar />
      <main className="relative z-10">
        {/* MVP Banner - centered for the whole hero section */}
        <div className="flex justify-center w-full mb-6">
          <span className="px-4 py-1 rounded-full bg-[var(--color-primary)] bg-opacity-10 text-white font-semibold font-kumbh-sans text-sm shadow-md border border-[var(--color-primary)]">ClaimReady is in beta development</span>
        </div>
        <div className="flex flex-col md:flex-row items-center justify-center min-h-screen relative mb-16 px-4 md:px-10">
          {/* Left: Claim with Confidence */}
          <div className="md:w-3/5 flex flex-col items-start justify-center mb-8 md:mb-0 md:pr-10">
            <h1 className="text-xl lg:text-7xl font-clash-display-semibold leading-tight text-left">
              Your Home Inventory, <span className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] bg-clip-text text-transparent">Automated</span>
            </h1>
            <p className="text-xl mt-6 mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)] text-left">
            Ditch manual spreadsheets and endless paperwork. ClaimReady automates your home inventory and creates bulletproof insurance claims, ensuring your belongings are fully valued and your payout is maximized.
            </p>
            <div className="flex flex-wrap gap-4 justify-start">
              <Link 
                href="/upload" 
                className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                hover:-translate-y-1
                shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)] font-kumbh-sans text-center flex items-center gap-2"
                onClick={() => posthog.capture('try_it_now_clicked')}
              >
                Try It Now
                <TiArrowRightThick className="inline-block pb-1" size={25} />
              </Link>
            </div>
          </div>
          {/* Right: Image */}
          <div className="md:w-2/5 w-full flex justify-center md:justify-end mt-8 md:mt-0">
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
          {/* Bouncing Down Arrow - only show at top of page */}
          {showArrow && (
            <div className="fixed left-0 right-0 flex justify-center" style={{ bottom: '5vh', zIndex: 9999 }}>
              <span className="animate-bounce text-5xl text-[var(--color-primary)]">&#8595;</span>
            </div>
          )}
        </div>
        {/* stats section - White */}
        <div className="bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4 mb-20">
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
                  <FaHome size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                 <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">10% of Homes</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">1 in 10 homes are affected by <br/>natural disasters.</p>
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
                   
                  <MdRealEstateAgent size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                 <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">6 Million Property Insurance Claims</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Over 6 million property insurance claims are filed per year.</p>
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
                <IoPeopleSharp size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                <h3 className="font-kumbh-sans text-[var(--color-primary)] text-lg font-bold mb-3 text-center">41% of People</h3>
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">41% of Americans live in <br/>diaster-declared zones.</p>
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

        {/* Disaster Showcase Cards Section */}
        <div className="container mx-auto px-4 mb-15">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {/* Card 1: Flood Damage */}
            <div className="bg-white rounded-xl shadow-2xl drop-shadow-lg overflow-hidden transition-transform duration-500 hover:-rotate-1 hover:scale-105 cursor-pointer flex flex-col items-center max-w-xs mx-auto">
              <div className="rounded-xl overflow-hidden w-full max-w-[500px]">
                <Image 
                  src="/flood.jpeg"
                  alt="Flood" 
                  width={600}
                  height={450}
                  className="w-full aspect-[4/3] rounded-lg"
                />
              </div>
            </div>
            {/* Card 2: Placeholder for future image */}
            <div className="bg-white rounded-xl shadow-2xl drop-shadow-lg overflow-hidden transition-transform duration-500 hover:rotate-1 hover:scale-105 cursor-pointer flex flex-col items-center max-w-xs mx-auto">
              <div className="rounded-xl overflow-hidden w-full max-w-[500px]">
                <Image 
                  src="/fire.jpg"
                  alt="Fire" 
                  width={600}
                  height={450}
                  className="w-full aspect-[4/3] rounded-lg"
                />
              </div>
            </div>
          </div>
        </div>

        <StickyHorizontalTimeline />

        {/* How It Works Section - White */}
        <div className="bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4 mt-15">
            <h2 className="text-5xl font-bold text-[var(--color-text-primary)] mb-8 text-center font-clash-display-semibold">Enter ClaimReady</h2>
            <p className="text-xl mb-8 leading-relaxed font-kumbh-sans text-[var(--color-text-secondary)] text-center ">
             With ClaimReady, we handle steps 2-6 of the current process, saving time and effort. 
            </p>
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
                <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Our powerful AI scans your photos, recognizes your belongings, and quickly obtains an accurate valuation.</p>
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
            <h2 className="text-5xl font-bold text-center mb-10 text-[var(--color-text-primary)] font-clash-display-semibold">What Makes ClaimReady Even Better</h2>
            
            <div className="max-w-5xl mx-auto text-[var(--color-text-primary)] mb-10">
              <p className="text-[var(--color-text-secondary)] mb-7 text-center font-kumbh-sans text-xl">
                ClaimReady has these additional features to make <br/> filing your claim to insurance even faster and easier.
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
                  <FaFileExport size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Export to CSV</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">We export your valuation to a CSV format, allowing you to directly submit it to your insurance.</p>
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
                  <RiAccountCircle2Fill size={45} color="var(--color-primary)" className="mb-3 mx-auto" />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center">Saved Account Info</h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">Never fear of losing your valuations with saved account information.</p>
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
            {/* Try It Now Button at the bottom */}
            <div className="flex justify-center mt-8">
              <Link 
                href="/upload" 
                className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                hover:-translate-y-1
                shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)] font-kumbh-sans"
              >
                Try It Now
                <TiArrowRightThick className="inline-block pb-1 pl-1" size={25} />
              </Link>
            </div>
          </div>
        </div>

        {/* Features Section - Black */}
        <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-5xl font-bold text-center mb-10 text-[var(--color-text-primary)] font-clash-display-semibold">Meet the Team</h2>  
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
                    src={Adi}
                    alt="Adi Parekh"
                    width={96} // Tailwind w-24 equivalent
                    height={96}
                    className="rounded-full object-cover mb-3 mx-auto"
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
                    src={Smyan}
                    alt="Smyan Vinu"
                    width={96} // Tailwind w-24 equivalent
                    height={96}
                    className="rounded-full object-cover mb-3 mx-auto"
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
                    src={Arnav}
                    alt="Arnav Mohanty"
                    width={96} // Tailwind w-24 equivalent
                    height={96}
                    className="rounded-full object-cover mb-3 mx-auto"
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
                    src={Soham}
                    alt="Soham Kundu"
                    width={96} // Tailwind w-24 equivalent
                    height={96}
                    className="rounded-full object-cover mb-3 mx-auto"
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
                    src={Jayanth}
                    alt="Jayanth Balu"
                    width={96} // Tailwind w-24 equivalent
                    height={96}
                    className="rounded-full object-cover mb-3 mx-auto"
                  />
                  <h3 className="text-[var(--color-primary)] font-bold mb-3 font-kumbh-sans text-center text-lg">
                    Jayanth Balu
                  </h3>
                  <p className="text-[var(--color-text-dark)] font-kumbh-sans text-center">
                    Computer Science & Data Science <br/>University of Wisconsin-Madison
                  </p>
                </motion.div>
              </div>
          </div>
        </div>
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