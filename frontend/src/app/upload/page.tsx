'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { useAuth } from '@/components/AuthContext';
import ItemTable from '@/components/ItemTable';
import posthog from '../../lib/posthog';

import { BorderBeam } from '@/components/magicui/border-beam';

// --- Add StackedImagePreview component ---
import React from 'react';

const StackedImagePreview: React.FC<{ files: File[] }> = ({ files }) => {
  const [previews, setPreviews] = useState<string[]>([]);
  const [hovered, setHovered] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1200);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!files.length) return;
    const readers = files.map(file => {
      return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(file);
      });
    });
    Promise.all(readers).then(setPreviews);
  }, [files]);

  const imgWidth = 208; // w-52 in px
  const imgHeight = 160; // h-40 in px
  const gap = 12; // px

  // Calculate images per row based on window width
  const maxStackWidth = Math.min(windowWidth, 900); // limit to 900px max for aesthetics
  const imagesPerRow = Math.max(1, Math.floor((maxStackWidth + gap) / (imgWidth + gap)));
  //const rowCount = Math.ceil(previews.length / imagesPerRow);
  //const unfoldedHeight = rowCount * (imgHeight * 0.6 + gap) + (imgHeight * 0.4); // 0.6 for overlap, 0.4 for last row

  // Calculate minimum width for the stack (default state)
  const minStackImages = Math.min(previews.length, 4);
  const minStackWidth = minStackImages * (imgWidth * 0.5); // 0.5 overlap for stack

  // Calculate grid width for unwound state
  //const gridWidth = hovered ? Math.min(imagesPerRow, previews.length) * (imgWidth + gap) - gap : undefined;

  // Calculate stack width for centering
  const stackWidth = (minStackImages - 1) * 24 + imgWidth;
  const stackCenterOffset = (minStackWidth - stackWidth) / 2;

  // Calculate max row width for centering the grid
  const maxRowImages = Math.min(imagesPerRow, previews.length);
  const containerGridWidth = maxRowImages * (imgWidth + gap) - gap;

  return (
    <div className="flex justify-center">
      <div
        className="relative inline-block mt-8 mb-8 group"
        style={{
          minWidth: hovered ? `${containerGridWidth}px` : `${minStackWidth}px`,
          width: hovered ? `${containerGridWidth}px` : undefined,
          minHeight: hovered ? `${Math.ceil(previews.length / imagesPerRow) * (imgHeight + gap)}px` : '160px',
          height: hovered ? `${Math.ceil(previews.length / imagesPerRow) * (imgHeight + gap)}px` : '160px',
          transition: 'height 0.5s, min-height 0.5s, min-width 0.5s, width 0.5s',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {previews.map((src, i) => {
          const style: React.CSSProperties = {
            transition: 'transform 0.5s',
            width: imgWidth,
            height: imgHeight,
            position: 'absolute',
            left: 0,
            top: 0,
          };
          const className = `object-cover rounded-lg shadow-lg border border-gray-300 z-${30 - i * 10}`;
          if (hovered) {
            // Calculate grid position, centering each row
            const row = Math.floor(i / imagesPerRow);
            const col = i % imagesPerRow;
            const rowCount = Math.ceil(previews.length / imagesPerRow);
            const imagesInThisRow = (row === rowCount - 1) ? (previews.length - row * imagesPerRow) : imagesPerRow;
            const rowWidth = imagesInThisRow * (imgWidth + gap) - gap;
            const rowLeftOffset = (containerGridWidth - rowWidth) / 2;
            const x = rowLeftOffset + (col * (imgWidth + gap));
            const y = row * (imgHeight + gap);
            style.transform = `rotate(0deg) translateX(${x}px) translateY(${y}px)`;
            style.opacity = 1;
            style.pointerEvents = undefined;
          } else {
            // Improved stack: small offset and rotation for up to 4 images, centered
            const stackIdx = Math.min(i, 3);
            const stackOffset = stackIdx * 24 + stackCenterOffset;
            const stackRot = [0, -6, 4, -8][stackIdx] || 0;
            style.transform = `rotate(${stackRot}deg) translateX(${stackOffset}px) translateY(0px)`;
            if (i >= 4) {
              style.opacity = 0;
              style.pointerEvents = 'none';
            }
            style.transformOrigin = 'bottom left';
          }
          return (
            <img
              key={i}
              src={src}
              alt={`Preview ${i + 1}`}
              className={className}
              style={style}
              onError={e => {
                e.currentTarget.style.background = '#eee';
                e.currentTarget.style.color = '#888';
                e.currentTarget.src = '';
                e.currentTarget.alt = 'Image failed to load';
              }}
            />
          );
        })}
      </div>
    </div>
  );
};

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
//goo
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
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
          // Remove the data URL prefix if present
          const base64Data = base64.includes(',') ? base64.split(',')[1] : base64;
          imageDataArray.push(base64Data);
        } else {
          setError('Only image files are supported. Please upload JPG, PNG, GIF, etc.');
          setIsUploading(false);
          return;
        }
      }

      setUploadProgress(50);

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
      console.log('🔗 Frontend using backend URL:', backendUrl);
      let response;
      if (files.length === 1) {
        // Single image: send as multipart/form-data
        const formData = new FormData();
        formData.append('image', files[0]);
        console.log('📤 Sending single image request to:', `${backendUrl}/api/analyze-image`);
        response = await fetch(`${backendUrl}/api/analyze-image`, {
          method: 'POST',
          body: formData,
        });
      } else {
        // Multi-image: send as JSON to /api/analyze-multiple-images
        console.log('📤 Sending multiple images request to:', `${backendUrl}/api/analyze-multiple-images`);
        response = await fetch(`${backendUrl}/api/analyze-multiple-images`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ images: imageDataArray }),
        });
      }
      console.log('📥 Response status:', response.status);
      console.log('📥 Response ok:', response.ok);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to analyze image(s)');
      }
      const result = await response.json();
      console.log('📥 Full backend response:', result);
      console.log('📥 Items array length:', result.items?.length || 0);
      console.log('📥 Images object keys:', Object.keys(result.images || {}));
      
      // Debug: Check if items exist and their structure
      if (result.items && Array.isArray(result.items)) {
        console.log('✅ Items found:', result.items.length);
        console.log('✅ First item:', result.items[0]);
        console.log('✅ All item codes:', result.items.map((item: any) => item.code));
      } else {
        console.log('❌ No items or items is not an array');
        console.log('❌ Result structure:', Object.keys(result));
      }
      
      setUploadProgress(100);
      if (result.items) {
        // For multi-image, group results by image if possible
        if (files.length > 1) {
          setSuccess(`Successfully analyzed ${files.length} images. Found ${result.total_items} items with total value: $${(result.total_value || 0).toFixed(2)}`);
        } else {
          const itemCount = result.items?.length || 0;
          // Calculate total value from items array
          const calculatedTotal = result.items?.reduce((sum: any, item: any) => sum + (typeof item.price_usd === 'string' ? parseFloat(item.price_usd) : item.price_usd || 0), 0) || 0;
          setSuccess(`Successfully analyzed 1 image. Found ${itemCount} items with total value: $${calculatedTotal.toFixed(2)}`);
        }
        setAnalysisResults(result);
        console.log('📊 Analysis results set:', result);
        console.log('📊 Items in analysis results:', result.items?.length || 0);
        console.log('📊 Images in analysis results:', Object.keys(result.images || {}).length);
        
        // Debug: Check what will be passed to ItemTable
        const itemsForTable = result.items || [];
        const totalValue = itemsForTable.reduce((sum: any, item: any) => sum + (item.price_usd || 0), 0);
        console.log('🎯 ItemTable will receive:', {
          items: itemsForTable.length,
          totalValue: totalValue,
          hasItems: itemsForTable.length > 0,
          firstItem: itemsForTable[0]
        });
        
        // Force test: Create a simple test item if no items are found
        if (!result.items || result.items.length === 0) {
          console.log('⚠️ No items found in response, creating test item');
          const testResult = {
            ...result,
            items: [{
              code: 'test_0',
              name: 'Test Item',
              category: 'Test Category',
              brand: 'Test Brand',
              condition: 'Good',
              price_usd: 100,
              description: 'This is a test item to verify the table is working',
              nullify: false
            }],
            images: {
              'test_0': 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiBmaWxsPSIjRkZGRkZGIi8+CjxwYXRoIGQ9Ik0zMiAxNkwyNCAyNEwzMiAzMkw0MCAyNEwzMiAxNloiIGZpbGw9IiM5Q0EzQUYiLz4KPC9zdmc+'
            }
          };
          setAnalysisResults(testResult);
          console.log('📊 Test results set instead');
        }
        
        // Remove images before storing in localStorage to avoid quota exceeded error
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { images, ...resultWithoutImages } = result;
        localStorage.setItem('analysisResults', JSON.stringify(resultWithoutImages));
      } else {
        setError('Analysis failed. Please try again.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze image(s)');
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
    ? Object.entries(analysisResults.images).map(([code, image]) => {
        // Find the corresponding item to get its bbox coordinates
        const item = analysisResults.items?.find((item: any) => item.code === code);
        const bbox = item?.bbox || [0, 0, 0, 0];
        
        const segment = {
          index: code, // Use the actual code instead of array index
          image: image as string,
          original_box: bbox as [number, number, number, number],
          original_size: [0, 0] as [number, number],
          normalized_size: [0, 0] as [number, number],
        };
        
        console.log('Creating segment:', { code, index: segment.index });
        return segment;
      }).filter(segment => segment.image) // Filter out any segments without images
    : [];

  console.log('Frontend segments created:', segments.map(s => s.index));
  console.log('Frontend analysisResults.images keys:', analysisResults?.images ? Object.keys(analysisResults.images) : []);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg-dark)]">
      <Navbar />

      <main className="flex-1 flex flex-col items-center p-8 bg-[var(--color-bg-dark)]" >
        
        <h1 className="text-3xl font-extrabold text-[var(--color-primary)] mb-8 font-kumbh-sans">Upload Your Pictures</h1>
        
        {/* Upload Area */}
        
        <div className="upload-area w-full max-w-3xl mx-auto">
          {!isUploading ? (
            <div className="relative">
              <div className="absolute inset-0 rounded-xl">
                <BorderBeam duration={6} size={200} borderWidth={2.5} colorFrom='var(--color-primary)' colorTo='var(--color-primary-dark)'/>
              </div>
              <div 
                className={`w-full  shadow-[0_0_20px_var(--shadow-color-primary)] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors relative overflow-hidden
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
            </div>
          ) : (
            <div className="relative">
              <div className="absolute inset-0 rounded-xl pointer-events-none">
                <BorderBeam duration={6} size={200} borderWidth={2.5} colorFrom='var(--color-primary)' colorTo='var(--color-primary-dark)'/>
              </div>
              <div className="w-full rounded-xl overflow-hidden bg-gray-900 shadow-lg flex flex-col items-center justify-center relative" style={{ minHeight: '300px' }}>
                <div className="flex flex-col items-center justify-center h-full w-full p-8">
                  <span className="text-sm font-medium text-white font-kumbh-sans mb-4">Analyzing Images. May take up to 2 minutes. Please retry if you get unsatisfactory results.</span>
                  <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500"></div>
                </div>
              </div>
            </div>
          )}

          {/* Show original image preview immediately after upload */}
          {files.length > 1 ? (
            <div className="flex flex-col items-center my-4">
              <h3 className="text-lg font-semibold mb-2 text-[var(--color-primary)] font-kumbh-sans">Selected Images</h3>
              {files.length > 1 && (
                <span className="text-xs text-gray-500 mb-2 font-kumbh-sans">(hover to expand)</span>
              )}
              <StackedImagePreview files={files} />
            </div>
          ) : originalImageUrl && (
            <div className="flex flex-col items-center my-4">
              <h3 className="text-lg font-semibold mb-2 text-[var(--color-primary)] font-kumbh-sans">Selected Images</h3>
              <img src={originalImageUrl} alt="Original Upload" className="w-52 h-40 object-cover rounded-lg shadow-lg border border-gray-300" />
            </div>
          )}

          {error && (
            <div className="mt-4 text-red-500 font-kumbh-sans">{error}</div>
          )}

          {success && (
            <div className="mt-4 text-green-500 font-kumbh-sans text-center w-full">{success}</div>
          )}

          <div className="mt-8 flex justify-center">
            {!analysisResults && (
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
            )}
            
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
              totalValue={analysisResults.total_value}
              totalItems={analysisResults.total_items}
              imagesProcessed={files.length}
              segments={segments}
              analysisResults={analysisResults}
            />
          </div>
        )}

      </main>
    </div>
  );
}
