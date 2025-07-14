'use client';
import { useEffect, useState } from 'react';
import { useAuth } from '@/components/AuthContext';
import { getUserJobs } from '@/lib/supabaseQueries';
import Link from 'next/link';
import Navbar from '@/components/Navbar';

export default function HistoryPage() {
  const { user, loading } = useAuth();
  const [jobs, setJobs] = useState<any[]>([]);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (user) {
      setFetching(true);
      getUserJobs(user.id).then(jobs => {
        setJobs(jobs);
        setFetching(false);
      });
    }
  }, [user]);

  if (loading) return <div>Loading...</div>;
  if (!user) return <div className="min-h-screen flex items-center justify-center">You must be logged in to view your history.</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 py-8 bg-[var(--color-bg-primary)]">
        <h1 className="text-4xl font-bold mb-6 text-center text-[var(--color-primary)] font-kumbh-sans">My Upload History</h1>
        {fetching ? (
          <div className="flex justify-center items-center h-32">Loading...</div>
        ) : jobs.length === 0 ? (
          <div className="text-center text-gray-500">No uploads found.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {jobs.map(job => (
              <Link key={job.id} href={`/results?job_id=${job.id}`} className="block bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-all">
                <div className="flex flex-col gap-2">
                  <div className="text-lg font-bold text-[var(--color-primary)]">Job ID: {job.id}</div>
                  <div className="text-sm text-gray-500">Created: {new Date(job.created_at).toLocaleString()}</div>
                  <div className="text-sm text-gray-500">Status: {job.status}</div>
                  <div className="text-sm text-gray-500">Items: {job.numItems ?? 0}</div>
                  <div className="text-sm text-gray-500">Total Value: ${job['total value']?.toLocaleString() ?? 0}</div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
} 