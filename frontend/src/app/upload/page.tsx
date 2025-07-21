'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { useAuth } from '@/components/AuthContext';
import ItemTable from '@/components/ItemTable';
import posthog from '../../lib/posthog';
export default function UploadPage() {
  useEffect(() => {
    posthog.capture('$pageview', { page: 'UploadPage' });
  }, []);
  const { user, loading, isGuest } = useAuth();
  const router = useRouter();
  // Redirect if not authenticated
  if (!loading && !user && !isGuest) {
    if (typeof window !== 'undefined') router.replace('/login');
    return null;
  }

  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<any>(null);
  //const [processingStatus, setProcessingStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [tosAccepted, setTosAccepted] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('tosAccepted') === 'true';
    }
    return false;
  });
  const [showTosModal, setShowTosModal] = useState(false);
  const [originalImageUrl, setOriginalImageUrl] = useState<string | null>(null);
  // Remove progressPercent, progressStage, progressPollRef, pollProgress, and related logic
  const progressPollRef = useRef<NodeJS.Timeout | null>(null);

  // Ensure TOS acceptance is synced with localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setTosAccepted(sessionStorage.getItem('tosAccepted') === 'true');
    }
  }, []);

  const handleTosAccept = () => {
    setTosAccepted(true);
    sessionStorage.setItem('tosAccepted', 'true');
    setShowTosModal(false);
    posthog.capture('tos_accepted');
    // If files are present, immediately start upload
    if (files.length > 0) {
      handleUpload();
    }
  };

  const handleTosDecline = () => {
    setShowTosModal(false);
  };

  const handleAnalyzeClick = () => {
    if (!tosAccepted) {
      setShowTosModal(true);
      posthog.capture('tos_modal_opened');
      return;
    }
    posthog.capture('analyze_images_clicked', { fileCount: files.length });
    handleUpload();
  };


  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files || [];
    const validFiles = Array.from(selectedFiles).filter((file: unknown) => {
      const f = file as File;
      return f.type === 'image/png' || f.type === 'image/jpeg';
    });
    if (validFiles.length === 0) {
      setError('Please select at least one image file');
      setOriginalImageUrl(null);
      return;
    }
    setFiles(validFiles as File[]);
    setError(null);
    // Show preview of the first image
    const reader = new FileReader();
    reader.onload = () => setOriginalImageUrl(reader.result as string);
    reader.readAsDataURL(validFiles[0]);
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
      return f.type === 'image/png' || f.type === 'image/jpeg';
    });
    if (validFiles.length === 0) {
      setError('Please drop at least one image file');
      setOriginalImageUrl(null);
      return;
    }
    setFiles(validFiles as File[]);
    setError(null);
    // Show preview of the first image
    const reader = new FileReader();
    reader.onload = () => setOriginalImageUrl(reader.result as string);
    reader.readAsDataURL(validFiles[0]);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one image file');
      return;
    }
    setIsUploading(true);
    setError(null);
    setSuccess(null);
    setUploadProgress(0);
    try {
      // Convert files to base64
      const imageDataArray = [];
      for (const file of files) {
        if (file.type.startsWith('image/')) {
          const base64 = await fileToBase64(file);
          imageDataArray.push(base64);
        } else {
          setError('Only image files are supported. Please upload JPG, PNG, GIF, etc.');
          setIsUploading(false);
          return;
        }
      }

      setUploadProgress(50);

      // Use geminiserver endpoints
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
      let response;
      if (files.length === 1) {
        // Single image: send as multipart/form-data
        const formData = new FormData();
        formData.append('image', files[0]);
        response = await fetch(`${backendUrl}/api/analyze-image`, {
          method: 'POST',
          body: formData,
        });
      } else {
        setError('Multiple image upload is not yet supported with the new binary upload. Please upload one image at a time.');
        setIsUploading(false);
        return;
      }
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze image');
      }
      const result = await response.json();
      setUploadProgress(100);
      if (result.status === 'success' || result.items) {
        const itemCount = result.items?.length || 0;
        // Calculate total value from items array
        const calculatedTotal = result.items?.reduce((sum: any, item: any) => sum + (typeof item.price_usd === 'string' ? parseFloat(item.price_usd) : item.price_usd || 0), 0) || 0;
        setSuccess(`Successfully analyzed ${files.length} image(s). Found ${itemCount} items with total value: $${calculatedTotal.toFixed(2)}`);
        setAnalysisResults(result);
        // Remove images before storing in localStorage to avoid quota exceeded error
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { images, ...resultWithoutImages } = result;
        localStorage.setItem('analysisResults', JSON.stringify(resultWithoutImages));
      } else {
        setError('Analysis failed. Please try again.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze image');
    } finally {
      setIsUploading(false);
    }
  };

  // Poll backend for progress
  // Remove progressPercent, progressStage, progressPollRef, pollProgress, and related logic

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (progressPollRef.current) {
        clearInterval(progressPollRef.current);
        progressPollRef.current = null;
      }
    };
  }, []);

  // Helper function to convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const segments = analysisResults && analysisResults.images
    ? Object.entries(analysisResults.images).map(([index, image]) => ({
        index: Number(index),
        image: image as string,
        original_box: [0, 0, 0, 0] as [number, number, number, number],
        original_size: [0, 0] as [number, number],
        normalized_size: [0, 0] as [number, number],
      }))
    : [];

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center p-8 bg-[var(--color-bg-primary)]" >
        <h1 className="text-3xl font-extrabold text-[var(--color-primary)] mb-8 font-kumbh-sans">Upload Your Pictures</h1>
        
        {/* Upload Area */}
        <div className="upload-area w-full max-w-3xl mx-auto">
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
                accept="image/jpg, image/png, image/gif, image/bmp, image/webp, image/jpeg" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleFileChange}
                multiple
              />
              
              {!files.length ? (
                <>
                  <div className="text-5xl mb-4">📸</div>
                  <p className="text-xl text-gray-600 mb-2 font-kumbh-sans">Drag and drop your images here</p>
                  <p className="text-gray-500 font-kumbh-sans">or click to browse files</p>
                  <p className="text-sm text-gray-400 mt-4 font-kumbh-sans">Supported formats: JPG, PNG, GIF, BMP, WEBP</p>
                </>
              ) : (
                <>
                  <p className="text-xl font-bold text-[var(--color-text-secondary-dark)] mb-2 font-kumbh-sans">Selected files:</p>
                  <p className="text-blue-600 font-medium">{files.length} file(s) selected</p>
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
            <div className="w-full rounded-xl overflow-hidden bg-gray-900 shadow-lg flex flex-col items-center justify-center" style={{ minHeight: '300px' }}>
              <div className="flex flex-col items-center justify-center h-full w-full p-8">
                <span className="text-sm font-medium text-white font-kumbh-sans mb-4">Analyzing Images</span>
                <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500"></div>
              </div>
            </div>
          )}

          {/* Show original image preview immediately after upload */}
          {originalImageUrl && (
            <div className="flex flex-col items-center my-8">
              <h3 className="text-lg font-semibold mb-2 text-[var(--color-primary)] font-kumbh-sans">Original Uploaded Image</h3>
              <img src={originalImageUrl} alt="Original Upload" className="max-w-full max-h-96 rounded-lg shadow-lg border border-gray-300" />
            </div>
          )}

          {error && (
            <div className="mt-4 text-red-500 font-kumbh-sans">{error}</div>
          )}

          {success && (
            <div className="mt-4 text-green-500 font-kumbh-sans text-center w-full">{success}</div>
          )}

          <div className="mt-8 flex justify-center">
            <button
              className={`px-8 py-3 rounded-lg font-medium transition-all duration-300 ease-in-out font-kumbh-sans ${
                files.length > 0 && !isUploading
                  ? 'bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white hover:-translate-y-1 shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)]'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed font-kumbh-sans'
              }`}
              onClick={handleAnalyzeClick}
              disabled={files.length === 0 || isUploading}
            >
              {isUploading ? 'Analyzing...' : 'Analyze Images'}
            </button>
          </div>

          {/* TOS Modal */}
          {showTosModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" style={{backdropFilter: 'blur(6px)'}}>
              <div className="bg-white rounded-lg shadow-lg p-8 max-w-lg w-full">
                <h2 className="text-xl font-bold mb-4 font-kumbh-sans">Terms of Service</h2>
                <div className="mb-6 max-h-60 overflow-y-auto text-gray-700 text-sm font-kumbh-sans">
                  <p>
                  By using this service, you agree to our Terms of Service. You acknowledge and consent that any images you upload may be analyzed using third-party AI tools for the purpose of item identification, classification, and valuation. ClaimReady does not guarantee the accuracy, completeness, or suitability of the results for official insurance or legal use. Uploaded content must not contain sensitive personal information, faces, medical data, or any materials prohibited by applicable law. Data may be temporarily stored and used to improve our services, but will not be sold or shared with unauthorized third parties. By continuing, you accept all responsibility for how the generated outputs are used and release ClaimReady from liability related to claim outcomes or financial decisions made using the tool.
                  </p>
                </div>
                <div className="flex justify-end gap-4">
                  <button
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 font-kumbh-sans"
                    onClick={handleTosDecline}
                  >
                    Decline
                  </button>
                  <button
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-kumbh-sans"
                    onClick={handleTosAccept}
                  >
                    Accept
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Results Area */}
        {analysisResults && (
          <div className="results-area w-full mt-12">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-[var(--color-text-primary)] font-kumbh-sans">
                Analysis Results
              </h2>
              <button
                onClick={() => {
                  setAnalysisResults(null);
                  setFiles([]);
                  setSuccess(null);
                  setError(null);
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-kumbh-sans"
              >
                New Analysis
              </button>
            </div>
            <ItemTable
              items={analysisResults.items || []}
              totalValue={analysisResults.total_value || 0}
              totalItems={analysisResults.total_items || analysisResults.items?.length || 0}
              imagesProcessed={analysisResults.images_processed || files.length}
              segments={segments}
            />
          </div>
        )}

      </main>
    </div>
  );
}
