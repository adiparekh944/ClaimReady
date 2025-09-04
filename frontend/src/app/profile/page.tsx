'use client';
import { useSupabaseAuth } from '../../components/SupabaseAuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Navbar from '@/components/Navbar';

export default function ProfilePage() {
  const { user, loading } = useSupabaseAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-dark)]">
        <Navbar />
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-[var(--color-primary)] text-lg">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-dark)]">
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-[var(--color-primary)] mb-8">Profile</h1>
        <div className="bg-[var(--color-bg-primary)] rounded-lg p-6">
          <div className="flex items-center space-x-4 mb-6">
            <div className="w-16 h-16 bg-[var(--color-primary)] rounded-full flex items-center justify-center text-white font-bold text-2xl">
              {user.name?.charAt(0).toUpperCase() || user.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">{user.name || 'User'}</h2>
              <p className="text-gray-600">{user.email}</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="border-t pt-4">
              <h3 className="font-semibold text-gray-900 mb-2">Account Information</h3>
              <p className="text-gray-600">Account created via Google OAuth</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 