'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSupabaseAuth } from '../../components/SupabaseAuthContext';
import { BorderBeam } from '@/components/magicui/border-beam';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

export default function LoginPage() {
  const { user, loading, signInWithEmail, signInWithGoogle } = useSupabaseAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const router = useRouter();
  const supabase = createClientComponentClient();

  useEffect(() => {
    if (user) {
      router.replace('/');
    }
  }, [user, router]);

  if (user) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    
    const { error } = await signInWithEmail(email, password);
    if (error) {
      setError(error.message);
    } else {
      setSuccess('Login successful! Redirecting...');
      router.push('/');
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      
      if (error) {
        setError(error.message);
      } else {
        setSuccess('Password reset email sent! Check your inbox.');
      }
    } catch (err) {
      setError('Failed to send reset email');
    }
  };

  const handleGuest = () => {
    // Guest mode - redirect to main page without authentication
    router.push('/');
  };

  const handleGoogleSignIn = async () => {
    await signInWithGoogle();
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
              
              <div className="mt-6">
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  className="w-full py-2 px-4 bg-white border border-gray-300 rounded-md font-semibold text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center"
                >
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Continue with Google
                </button>
              </div>
              
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