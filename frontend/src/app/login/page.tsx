'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
// import { useNextAuth } from '../../components/NextAuthContext';
import { BorderBeam } from '@/components/magicui/border-beam';
// import NextAuthGoogleSignInButton from '../../components/NextAuthGoogleSignInButton';

export default function LoginPage() {
  // const { user, loading } = useNextAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const router = useRouter();

  // useEffect(() => {
  //   if (user) {
  //     router.replace('/');
  //   }
  // }, [user, router]);

  // if (user) {
  //   return null;
  // }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    // Note: Email/password login not implemented yet with NextAuth
    setError('Email/password login not available. Please use Google Sign-In.');
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    // Note: Password reset not implemented yet with NextAuth
    setError('Password reset not available. Please use Google Sign-In.');
  };

  const handleGuest = () => {
    // Note: Guest mode not implemented yet with NextAuth
    setError('Guest mode not available. Please use Google Sign-In.');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-dark)] font-kumbh-sans">
      <div className="w-full max-w-md relative rounded-md px-6 py-8 bg-[var(--color-bg-primary)] shadow-[0_0_40px_var(--shadow-color-primary)]">
        <BorderBeam duration={8} size={400} borderWidth={2.5} colorFrom='var(--color-primary)' colorTo='var(--color-primary-dark)'/>
        
          <h2 className="text-3xl font-bold mb-6 text-center text-[var(--color-primary)]">Login</h2>
          
          {!showForgotPassword ? (
            <>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium mb-1">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    placeholder="Enter your email"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    placeholder="Enter your password"
                  />
                </div>
                {error && <div className="text-red-600 text-sm text-center">{error}</div>}
                {success && <div className="text-green-600 text-sm text-center">{success}</div>}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors"
                >
                  {loading ? 'Logging in...' : 'Continue'}
                </button>
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => setShowForgotPassword(true)}
                    className="text-[var(--color-primary)] hover:underline text-sm"
                  >
                    Forgot your password?
                  </button>
                </div>
              </form>
              
              <div className="mt-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-gray-300" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-[var(--color-bg-primary)] text-gray-500">OR</span>
                  </div>
                </div>
              </div>
              
              {/* <div className="mt-6">
                <NextAuthGoogleSignInButton />
              </div> */}
              
              <div className="mt-6 flex flex-col items-center">
                <span className="text-gray-500 text-sm mb-2">or</span>
                <button
                  type="button"
                  onClick={handleGuest}
                  className="w-full py-2 px-4 bg-gray-200 text-[var(--color-primary)] rounded-md font-semibold hover:bg-gray-300 transition-colors"
                >
                  Try as Guest
                </button>
              </div>
            </>
          ) : (
            <form onSubmit={handleForgotPassword} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                  placeholder="Enter your email"
                />
              </div>
              {error && <div className="text-red-600 text-sm text-center">{error}</div>}
              {success && <div className="text-green-600 text-sm text-center">{success}</div>}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors"
              >
                {loading ? 'Sending...' : 'Send Reset Email'}
              </button>
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(false)}
                  className="text-[var(--color-primary)] hover:underline text-sm"
                >
                  Back to Login
                </button>
              </div>
            </form>
            
          )}
          
          <p className="mt-4 text-center text-sm text-[var(--color-text-dark)]">
            Don&apos;t have an account?{' '}
            <a href="/signup" className="text-[var(--color-primary)] hover:underline">Sign up</a>
          </p>
      </div>
    </div>
  );
} 