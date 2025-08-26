'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function ResetPasswordPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to login page since password reset is not available with Google OAuth
    router.replace('/login');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-primary)] font-kumbh-sans">
      <div className="w-full max-w-md bg-white rounded-lg shadow-lg p-8 text-center">
        <h2 className="text-3xl font-bold mb-6 text-center text-[var(--color-primary)]">Password Reset</h2>
        <p className="text-gray-600 text-center mb-6">
          Password reset is not available with Google OAuth authentication.
        </p>
        <p className="text-gray-600 text-center mb-6">
          Please use Google Sign-In to access your account.
        </p>
        
        <Link 
          href="/login"
          className="inline-block w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors"
        >
          Go to Login
        </Link>
      </div>
    </div>
  );
} 