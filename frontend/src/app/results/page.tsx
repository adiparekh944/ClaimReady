'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { motion } from 'framer-motion';
import { useSearchParams } from 'next/navigation';
import { getLatestJobResult, getJobResultById, getMultipleJobResults } from '@/lib/supabaseQueries';
import ItemCard from '@/components/ItemCard';
/*import VoiceAssistant from '@/components/VoiceAssistant';*/
import { useSupabaseAuth } from '@/components/SupabaseAuthContext';
import { useRouter } from 'next/navigation';

// Create a separate component for the main content
function ResultsContent() {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [jobCount, setJobCount] = useState<number>(0);
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');
  const jobIds = searchParams.get('job_ids');

  useEffect(() => {
    async function fetchResults() {
      try {
        setLoading(true);

        let data;
        if (jobIds) {
          // Multiple job IDs - fetch and combine results from all jobs
          const jobIdArray = jobIds.split(',').filter(id => id.trim());
          console.log(`Fetching results for multiple job IDs: ${jobIdArray.join(', ')}`);
          data = await getMultipleJobResults(jobIdArray);
          setJobCount(jobIdArray.length);
        } else if (jobId) {
          // Single job ID
          console.log(`Fetching results for job ID: ${jobId}`);
          data = await getJobResultById(jobId);
          setJobCount(1);
        } else {
          // Fallback to latest job result if no job_id is provided
          console.log('No job ID provided, fetching latest result');
          data = await getLatestJobResult();
          setJobCount(1);
        }
        
        if (data) {
          console.log('Data retrieved successfully:', data);
          setResults(data);
        } else {
          console.log("No data found in Supabase");
          console.log("ignore", usingSampleData);
          setError('No results found. Please try uploading a video first.');

          setUsingSampleData(true);
        }
      } catch (err) {
        console.error('Error fetching results:', err);
        setError('Failed to load results. Please try again later.');
      } finally {
        setLoading(false);
      }
    }

    fetchResults();
  }, [jobId, jobIds]);

  // Add handlers for editing and removing items
  const handleEdit = (key: string, field: string, value: any) => {
    setResults((prev: any) => {
      if (!prev) return prev;
      return {
        ...prev,
        [key]: {
          ...prev[key],
          [field]: value,
        },
      };
    });
  };
  const handleRemove = (key: string) => {
    setResults((prev: any) => {
      if (!prev) return prev;
      const newResults = { ...prev };
      delete newResults[key];
      return newResults;
    });
  };

  // Calculate total value and item count if results are available
  const totalValue = results ? Object.values(results).reduce((sum: number, item: any) => 
    sum + (item.estimated_price || 0), 0) : 0;
  const itemCount = results ? Object.keys(results).length : 0;

  function convertResultsToCSV(results: any) {
    if (!results) return '';
    const items = Object.values(results) as any[];
    if (items.length === 0) return '';
    const headers = Object.keys(items[0]);
    const csvRows = [headers.join(',')];
    for (const item of items) {
      const row = headers.map(h => {
        let val = (item as any)[h];
        if (typeof val === 'string') {
          val = '"' + val.replace(/"/g, '""') + '"';
        }
        return val;
      });
      csvRows.push(row.join(','));
    }
    return csvRows.join('\n');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      
      <div className=" mx-auto px-4 py-8 bg-[var(--color-bg-primary)]">
        <h1 className="text-5xl font-bold mb-6 text-center text-[var(--color-primary)] font-kumbh-sans">Inventory Results</h1>
        
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p>{error}</p>
            <Link href="/upload" className="text-blue-500 underline mt-2 inline-block">
              Go to Upload Page
            </Link>
          </div>
        ) : (
          <>
            {jobIds && (
              <div className="bg-blue-100 border border-blue-300 text-blue-700 px-4 py-3 rounded mb-4 font-kumbh-sans">
                <p>Viewing combined results from {jobCount} processed files</p>
                <p className="text-sm mt-1">Job IDs: {jobIds}</p>
              </div>
            )}
            {jobId && !jobIds && (
              <div className="bg-blue-100 border border-blue-300 text-blue-700 px-4 py-3 rounded mb-4 font-kumbh-sans">
                <p>Viewing results for job: {jobId}</p>
              </div>
            )}
            
            {/* Summary Card */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="bg-[var(--color-bg-primary)] rounded-lg shadow-md p-6 mb-8"
            >
              <h2 className="text-2xl font-semibold mb-4 text-[var(--color-primary)] font-kumbh-sans">
                {jobCount > 1 ? 'Combined Inventory Summary' : 'Inventory Summary'}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-200 rounded-lg p-4 shadow-[0_0_20px_#3b82f6]">
                  <p className="text-sm text-[var(--color-text-dark)] font-kumbh-sans">Total Estimated Value</p>
                  <p className="text-2xl font-bold text-blue-600 font-black-future">${totalValue.toLocaleString()}</p>
                </div>
                <div className="bg-green-100 rounded-lg p-4 shadow-[0_0_20px_#16a34a]">
                  <p className="text-sm text-[var(--color-text-dark)] font-kumbh-sans">Items Identified</p>
                  <p className="text-2xl font-bold text-green-600 font-black-future">{itemCount}</p>
                </div>
                {jobCount > 1 && (
                  <div className="bg-purple-100 rounded-lg p-4 shadow-[0_0_20px_#9333ea]">
                    <p className="text-sm text-[var(--color-text-dark)] font-kumbh-sans">Files Processed</p>
                    <p className="text-2xl font-bold text-purple-600 font-black-future">{jobCount}</p>
                  </div>
                )}
              </div>
            </motion.div>
            
            {/* Export to CSV Button */}
            {results && (
              <div className="flex justify-end mb-4">
                <button
                  className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors shadow font-kumbh-sans"
                  onClick={() => {
                    const csv = convertResultsToCSV(results);
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'inventory.csv';
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Export to CSV
                </button>
              </div>
            )}

            {/* Items Grid */}
            <h2 className="text-2xl font-bold mb-4 text-[var(--color-primary)] font-kumbh-sans">
              {jobCount > 1 ? 'All Identified Items' : 'Identified Items'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 font-kumbh-sans">
              {results && Object.entries(results).map(([key, item]: [string, any], index) => (
                <ItemCard key={key} itemKey={key} item={item} index={index} onEdit={handleEdit} onRemove={handleRemove} />
              ))}
            </div>
            
            {/* Voice Assistant 
            {jobId && results && (
              <VoiceAssistant jobId={jobId} itemsData={results} />
            )} */}
            
            <div className="mt-24 text-center">
              <Link 
                href="/upload" 
                className="rounded-[1.15rem] px-6 py-3 bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-primary-dark)] text-white transition-all duration-500 
                
                shadow-[0_0_20px_var(--shadow-color-primary)] hover:shadow-[0_0_25px_var(--shadow-color-primary-hover)] font-kumbh-sans"
              >
                Upload Another Video
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Main component with Suspense
export default function ResultsPage() {
  const { user, loading } = useSupabaseAuth();
  const router = useRouter();
  if (!loading && !user) {
    if (typeof window !== 'undefined') router.replace('/login');
    return null;
  }
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ResultsContent />
    </Suspense>
  );
}