'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { uploadFileToSupabase } from '@/components/fileUpload';
import Image from 'next/image';
import { motion } from 'framer-motion';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showVisualization, setShowVisualization] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to fetch the latest frame
  const fetchLatestFrame = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/latest-frame');
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setCurrentFrame(url);
      }
    } catch (err) {
      console.error('Error fetching frame:', err);
    }
  };

  // Start polling for frames when processing starts
  useEffect(() => {
    if (isProcessing && showVisualization) {
      frameIntervalRef.current = setInterval(fetchLatestFrame, 1000); // Poll every 1 second
    } else {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    }
    // disable visualization always
    setShowVisualization(false);

    return () => {
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    };
  }, [isProcessing, showVisualization]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    if (selectedFile && !selectedFile.type.startsWith('video/')) {
      setError('Please select a video file');
      return;
    }
    setFile(selectedFile);
    setError(null);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files?.[0] || null;
    if (droppedFile && !droppedFile.type.startsWith('video/')) {
      setError('Please drop a video file');
      return;
    }
    
    setFile(droppedFile);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a video file first');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);

    try {
      // Step 1: Create a job ID
      const jobResponse = await fetch('http://localhost:8080/api/create-job', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!jobResponse.ok) {
        throw new Error('Failed to create job');
      }

      const { job_id } = await jobResponse.json();
      setUploadProgress(33);

      // Step 2: Upload to Supabase with job ID
      const result = await uploadFileToSupabase(file, job_id, "video");
      setUploadProgress(66);

      if (showVisualization) {
        activateProcessing();
      }


      // Step 3: Send the Supabase URL to backend for processing
      const processResponse = await fetch('http://localhost:8080/api/process-video', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileUrl: result.url,
          job_id: job_id,
          show_display: showVisualization
        }),
      });

      if (!processResponse.ok) {
        throw new Error('Failed to start video processing');
      }

      if (!showVisualization) {
        setIsProcessing(false);
      }

      setUploadProgress(100);

      // Redirect to results page
      setTimeout(() => {
        router.push(`/results?job_id=${job_id}`);
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload video');
    } finally {
      setIsUploading(false);
    }
  };

  const activateProcessing = () => {
    setTimeout(() => {
      setIsProcessing(true);
    }, 3000);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center p-8 bg-[var(--color-bg-primary)]" >
        <h1 className="text-3xl font-extrabold text-[var(--color-primary)] mb-8">Upload Your Pictures or Videos</h1>
        
        <div className="max-w-3xl w-full">
          {!isUploading ? (
            <div 
              className={`w-full border-3 shadow-[0_0_20px_var(--shadow-color-primary)] border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors
                ${isDragging ? 'border-[var(--color-primary)] bg-gray-50' : 'border-[var(--color-primary)] hover:border-[var(--color-primary)] hover:bg-gray-50'}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{ minHeight: '300px' }}
            >
              <input 
                type="file" 
                accept="video/*" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileChange}
              />
              
              {!file ? (
                <>
                  <div className="text-5xl mb-4">🎥</div>
                  <p className="text-xl text-gray-600 mb-2">Drag and drop your video here</p>
                  <p className="text-gray-500">or click to browse files</p>
                  <p className="text-sm text-gray-400 mt-4">Supported formats: MP4</p>
                </>
              ) : (
                <>
                  <div className="text-4xl mb-4">🎥</div>
                  <p className="text-xl font-bold text-[var(--color-text-secondary-dark)] mb-2">Selected file:</p>
                  <p className="text-blue-600 font-medium">{file.name}</p>
                  <p className="text-gray-500 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  <button 
                    className="mt-4 text-sm text-red-500 hover:text-red-700"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                  >
                    Remove file
                  </button>
                </>
              )}
            </div>
          ) : (
            <div className="w-full rounded-xl overflow-hidden bg-gray-900 shadow-lg" style={{ minHeight: '300px' }}>
              {currentFrame && (
                <div className="relative">
                  <Image 
                    src={currentFrame} 
                    alt="Live analysis frame" 
                    className="w-full"
                    style={{ maxHeight: '400px', objectFit: 'contain' }}
                  />
                </div>
              )}
              <div className="p-4 bg-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">Processing Video</span>
                  <span className="text-sm font-medium text-white">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 text-red-500">{error}</div>
          )}

          {success && (
            <div className="mt-4 text-green-500">{success}</div>
          )}

          <div className="mt-8 flex items-center justify-between">
            <button
              className={`px-8 py-3 rounded-lg font-medium transition-all duration-300 ease-in-out ${
                file && !isUploading
                  ? 'bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white hover:-translate-y-1 shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)]'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading ? 'Analyzing...' : 'Analyze Video'}
            </button>

            <label className={`flex items-center space-x-2 ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={showVisualization}
                onChange={(e) => setShowVisualization(e.target.checked)}
                disabled={isUploading}
                className="form-checkbox h-5 w-5 text-blue-600 focus:ring-blue-500"
              />
              <span className={`text-[var(--color-text-primary)] ${isUploading ? 'text-[var(--color-text-secondary)]' : ''}`}>Visualize Processing</span>
            </label>
          </div>
          
          
          {/* --- TIPS SECTION --- */}
          <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-4xl font-bold text-[var(--color-text-primary)] mb-8 text-center">Tips for Best Outcomes</h2>
            <div className="max-w-3xl mx-auto space-y-8 mb-8">
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1">1</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg">Take clear and steady pictures</h3>
                  <p className="text-[var(--color-text-secondary)]">This helps the AI model recognize your belongings.</p>
                </div>
              </motion.div>

              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1">2</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg">Good Lighting</h3>
                  <p className="text-[var(--color-text-secondary)]">Make sure your pictures are well-lit.</p>
                </div>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1">3</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg">Many Angles.</h3>
                  <p className="text-[var(--color-text-secondary)]">Try and get as many angles of your belongingings as possible. This helps us make sure we don't miss any hidden ones.</p>
                </div>
              </motion.div>
            </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
