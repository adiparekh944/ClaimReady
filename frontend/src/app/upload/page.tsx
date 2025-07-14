'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { useAuth } from '@/components/AuthContext';

export default function UploadPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  // Redirect if not authenticated
  if (!loading && !user) {
    if (typeof window !== 'undefined') router.replace('/login');
    return null;
  }

  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showVisualization, setShowVisualization] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [fastMode, setFastMode] = useState(false); // OPTIMIZATION: Add fast mode state
  //const [processingStatus, setProcessingStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to fetch the latest frame
  const fetchLatestFrame = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
      const response = await fetch(`${backendUrl}/api/latest-frame`);
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
    if (showVisualization) {
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
  }, [showVisualization]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files || [];
    const validFiles = Array.from(selectedFiles).filter((file: unknown) => {
      const f = file as File;
      return f.type.startsWith('video/') || f.type.startsWith('image/');
    });
    if (validFiles.length === 0) {
      setError('Please select at least one video or image file');
      return;
    }
    setFiles(validFiles as File[]);
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
    
    const droppedFiles = e.dataTransfer.files || [];
    const validFiles = Array.from(droppedFiles).filter((file: unknown) => {
      const f = file as File;
      return f.type.startsWith('video/') || f.type.startsWith('image/');
    });
    if (validFiles.length === 0) {
      setError('Please drop at least one video or image file');
      return;
    }
    
    setFiles(validFiles as File[]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!user) {
      router.push('/login');
      return;
    }
    if (files.length === 0) {
      setError('Please select at least one video or image file');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);

    try {
      // Step 1: Create a job ID (only needed for single file)
      let job_id: string | undefined;
      if (files.length === 1) {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
        const jobResponse = await fetch(`${backendUrl}/api/create-job`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: user?.id }),
          // Add timeout for job creation
          signal: AbortSignal.timeout(30000), // 30 seconds
        });

        if (!jobResponse.ok) {
          throw new Error('Failed to create job');
        }

        const jobData = await jobResponse.json();
        job_id = jobData.job_id;
        setUploadProgress(33);
      }

      // Step 2: Use the unified upload and process endpoint
      const formData = new FormData();
      files.forEach(file => formData.append('file', file));
      if (job_id) {
        formData.append('job_id', job_id);
      }
      formData.append('show_display', showVisualization.toString());
      formData.append('fast_mode', fastMode.toString()); // OPTIMIZATION: Add fast mode parameter

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
      
      // Create a controller for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout
      
      try {
        const processResponse = await fetch(`${backendUrl}/api/upload-and-process`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!processResponse.ok) {
          const errorData = await processResponse.json();
          throw new Error(errorData.error || 'Failed to process files');
        }

        const result = await processResponse.json();
        setUploadProgress(100);

        // Handle response based on number of files
        if (files.length === 1 && result.job_id) {
          // Single file - redirect to results page
          setTimeout(() => {
            router.push(`/results?job_id=${result.job_id}`);
          }, 2000);
        } else if (result.job_ids && result.job_ids.length > 0) {
          // Multiple files - show summary and redirect to first job
          const successfulCount = result.successful || 0;
          const failedCount = result.failed || 0;
          
          setSuccess(`Successfully processed ${successfulCount} files${failedCount > 0 ? `, ${failedCount} failed` : ''}`);
          
          // Redirect to results page with all job IDs
          setTimeout(() => {
            const jobIdsParam = result.job_ids.join(',');
            router.push(`/results?job_ids=${jobIdsParam}`);
          }, 3000);
        } else {
          // No successful jobs
          setError('No files were processed successfully');
        }
      } catch (fetchError) {
        clearTimeout(timeoutId);
        if (fetchError instanceof Error && fetchError.name === 'AbortError') {
          throw new Error('Request timed out. Video processing is taking longer than expected. Please try again or use a shorter video.');
        }
        throw fetchError;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload files');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center p-8 bg-[var(--color-bg-primary)]" >
        <h1 className="text-3xl font-extrabold text-[var(--color-primary)] mb-8 font-kumbh-sans">Upload Your Pictures or Videos</h1>
        
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
                accept="video/*,image/*" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileChange}
                multiple
              />
              
              {!files.length ? (
                <>
                  <div className="text-5xl mb-4">📸</div>
                  <p className="text-xl text-gray-600 mb-2 font-kumbh-sans">Drag and drop your videos or images here</p>
                  <p className="text-gray-500 font-kumbh-sans">or click to browse files</p>
                  <p className="text-sm text-gray-400 mt-4 font-kumbh-sans">Supported formats: MP4, JPG, PNG, GIF</p>
                </>
              ) : (
                <>
                  <div className="text-4xl mb-4">{files[0].type.startsWith('image/') ? '📸' : '🎥'}</div>
                  <p className="text-xl font-bold text-[var(--color-text-secondary-dark)] mb-2 font-kumbh-sans">Selected files:</p>
                  <p className="text-blue-600 font-medium">{files.map(file => file.name).join(', ')}</p>
                  <p className="text-gray-500 mt-1">{(files.reduce((total, file) => total + file.size, 0) / (1024 * 1024)).toFixed(2)} MB</p>
                  <button 
                    className="mt-4 text-sm text-red-500 hover:text-red-700"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFiles([]);
                    }}
                  >
                    Remove files
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
                  <span className="text-sm font-medium text-white font-kumbh-sans">Processing Videos</span>
                  <span className="text-sm font-kumbh-sans font-medium text-white">{uploadProgress}%</span>
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
              className={`px-8 py-3 rounded-lg font-medium transition-all duration-300 ease-in-out font-kumbh-sans ${
                files.length > 0 && !isUploading
                  ? 'bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white hover:-translate-y-1 shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)]'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed font-kumbh-sans'
              }`}
              onClick={handleUpload}
              disabled={files.length === 0 || isUploading}
            >
              {isUploading ? 'Analyzing...' : `Analyze ${files[0]?.type.startsWith('image/') ? 'Images' : 'Videos'}`}
            </button>

            {/* Fast Mode Toggle */}
            <label className={`flex items-center space-x-2 ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={fastMode}
                onChange={(e) => setFastMode(e.target.checked)}
                disabled={isUploading}
                className="form-checkbox h-5 w-5 text-blue-600 focus:ring-blue-500"
              />
              <span className={`text-[var(--color-text-primary)] ${isUploading ? 'text-[var(--color-text-secondary)]' : ''}`}>
                Fast Mode (No Price Estimation)
              </span>
            </label>

            {/* Fast Mode Info */}
            {fastMode && (
              <div className="mt-2 text-sm text-blue-600 bg-blue-50 p-2 rounded">
                <p>⚡ Fast Mode: Object detection only, no price estimation. 3-5x faster processing.</p>
              </div>
            )}

            {/*<label className={`flex items-center space-x-2 ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={showVisualization}
                onChange={(e) => setShowVisualization(e.target.checked)}
                disabled={isUploading}
                className="form-checkbox h-5 w-5 text-blue-600 focus:ring-blue-500"
              />
              <span className={`text-[var(--color-text-primary)] ${isUploading ? 'text-[var(--color-text-secondary)]' : ''}`}>Visualize Processing</span>
            </label>
            */}
          </div>
          
          
          {/* --- TIPS SECTION --- */}
          <div className="py-20 bg-[var(--color-bg-primary)]">
          <div className="container mx-auto px-4">
            <h2 className="text-4xl font-bold text-[var(--color-text-primary)] mb-8 text-center font-black-future">Tips for Best Outcomes</h2>
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
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">Take clear and steady pictures</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">This helps the AI model recognize your belongings.</p>
                </div>
              </motion.div>

              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">2</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">Good Lighting</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Make sure your pictures are well-lit.</p>
                </div>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.3 }}
                viewport={{ once: true }}
                className="flex items-start gap-4"
              >
                <div className="bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] shadow-[0_0_15px_var(--shadow-color-primary)] text-white font-bold rounded-full w-10 h-10 flex items-center justify-center flex-shrink-0 mt-1 font-black-future">3</div>
                <div>
                  <h3 className="font-medium text-[var(--color-text-primary)] text-lg font-kumbh-sans">Many Angles</h3>
                  <p className="text-[var(--color-text-secondary)] font-kumbh-sans">Try and get as many angles of your belongings as possible. This helps us make sure we don&apos;t miss any hidden ones.</p>
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
