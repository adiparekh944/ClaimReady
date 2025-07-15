'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { useAuth } from '@/components/AuthContext';
import ItemTable from '@/components/ItemTable';

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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<any>(null);
  //const [processingStatus, setProcessingStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);



  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files || [];
    const validFiles = Array.from(selectedFiles).filter((file: unknown) => {
      const f = file as File;
      return f.type.startsWith('image/');
    });
    if (validFiles.length === 0) {
      setError('Please select at least one image file');
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
      return f.type.startsWith('image/');
    });
    if (validFiles.length === 0) {
      setError('Please drop at least one image file');
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
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
      
      let response;
      if (files.length === 1) {
        // Single image
        response = await fetch(`${backendUrl}/api/analyze-image`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            image: imageDataArray[0]
          }),
        });
      } else {
        // Multiple images
        response = await fetch(`${backendUrl}/api/analyze-multiple-images`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            images: imageDataArray
          }),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze images');
      }

      const result = await response.json();
      setUploadProgress(100);

      if (result.status === 'success') {
        const itemCount = result.items?.length || 0;
        // Calculate total value from items array
        const calculatedTotal = result.items?.reduce((sum: any, item: any) => sum + (typeof item.price === 'string' ? parseFloat(item.price) : item.price || 0), 0) || 0;
        setSuccess(`Successfully analyzed ${files.length} image(s). Found ${itemCount} items with total value: $${calculatedTotal.toFixed(2)}`);
        
        // Store results for display in the table
        setAnalysisResults(result);
        
        // Store results in localStorage for results page as well
        localStorage.setItem('analysisResults', JSON.stringify(result));
      } else {
        setError('Analysis failed. Please try again.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze images');
    } finally {
      setIsUploading(false);
    }
  };

  // Helper function to convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1 flex flex-col items-center p-8 bg-[var(--color-bg-primary)]" >
        <h1 className="text-3xl font-extrabold text-[var(--color-primary)] mb-8 font-kumbh-sans">Upload Your Pictures</h1>
        
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
                accept="image/*" 
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
            <div className="w-full rounded-xl overflow-hidden bg-gray-900 shadow-lg" style={{ minHeight: '300px' }}>
              <div className="p-4 bg-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white font-kumbh-sans">Analyzing Images</span>
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
            <div className="mt-4 text-red-500 font-kumbh-sans">{error}</div>
          )}

          {success && (
            <div className="mt-4 text-green-500 font-kumbh-sans">{success}</div>
          )}

          <div className="mt-8 flex justify-center">
            <button
              className={`px-8 py-3 rounded-lg font-medium transition-all duration-300 ease-in-out font-kumbh-sans ${
                files.length > 0 && !isUploading
                  ? 'bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white hover:-translate-y-1 shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)]'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed font-kumbh-sans'
              }`}
              onClick={handleUpload}
              disabled={files.length === 0 || isUploading}
            >
              {isUploading ? 'Analyzing...' : 'Analyze Images'}
            </button>
          </div>
          
          {/* Analysis Results */}
          {analysisResults && (
            <div className="mt-8">
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
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
