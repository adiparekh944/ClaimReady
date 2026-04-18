'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthContext';
import { BorderBeam } from '@/components/magicui/border-beam';
import SupabaseGoogleSignInButton from '@/components/SupabaseGoogleSignInButton';
import { ShineBorder } from "@/components/magicui/shine-border";


export default function LoginPage() {
  const { user, loading, signIn, resetPassword, signInAsGuest, signInWithGoogle } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (user) {
      const path = (() => {
        try {
          const p = localStorage.getItem('postLoginRedirect');
          if (p) {
            localStorage.removeItem('postLoginRedirect');
            return p;
          }
        } catch {}
        return '/upload';
      })();
      router.replace(path);
    }
  }, [user, router]);

  if (user) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    const res = await signIn(email, password);
    if (res?.error) {
      setError(res.error.message || 'Failed to sign in');
    } else {
      const path = (() => {
        try {
          const p = localStorage.getItem('postLoginRedirect');
          if (p) {
            localStorage.removeItem('postLoginRedirect');
            return p;
          }
        } catch {}
        return '/upload';
      })();
      router.replace(path);
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
    const res = await resetPassword(email);
    if (res?.error) {
      setError(res.error.message || 'Failed to send reset email');
    } else {
      setSuccess('Password reset email sent. Check your inbox.');
    }
  };

  const handleGuest = () => {
    signInAsGuest();
    const path = (() => {
      try {
        const p = localStorage.getItem('postLoginRedirect');
        if (p) {
          localStorage.removeItem('postLoginRedirect');
          return p;
        }
      } catch {}
      return '/upload';
    })();
    router.replace(path);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-primary)] font-kumbh-sans">
      <div className="w-full max-w-md relative rounded-md px-6 py-8 bg-white">
        <ShineBorder shineColor={["#ffffff", "#0051ff"]} duration={20} borderWidth={3} />
        
          <h2 className="text-3xl font-just-sans mb-6 text-center text-[var(--color-primary)]">Login</h2>
          
          {!showForgotPassword ? (
            <>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-just-sans mb-1">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    style= {{fontFamily: "var(--font-geist-sans)"}}
                    placeholder="Enter your email"
                  />
                </div>
                <div>
                  <label className="block text-sm font-just-sans mb-1">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
                    style= {{fontFamily: "var(--font-geist-sans)"}}
                    placeholder="Enter your password"
                  />
                </div>
                {error && <div className="text-red-600 text-sm text-center">{error}</div>}
                {success && <div className="text-green-600 text-sm text-center">{success}</div>}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-just-sans hover:bg-[var(--color-primary-dark)] transition-colors"
                >
                  {loading ? 'Logging in...' : 'Continue'}
                </button>
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => setShowForgotPassword(true)}
                    className="text-[var(--color-primary)] hover:underline text-sm font-just-sans"
                  >
                    Forgot your password?
                  </button>
                </div>
              </form>
              
              <div className="mt-6 mb-10">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-gray-300" />
                  </div>
                </div>
              </div>
              
              <div className="mt-6 font-just-sans">
                <SupabaseGoogleSignInButton loading={loading} onClick={async () => { await signInWithGoogle(); }} />
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
                  style={{fontFamily: "var(--font-geist-sans)"}}
                  placeholder="Enter your email"
                />
              </div>
              {error && <div className="text-red-600 text-sm text-center">{error}</div>}
              {success && <div className="text-green-600 text-sm text-center">{success}</div>}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-just-sans hover:bg-[var(--color-primary-dark)] transition-colors"
              >
                {loading ? 'Sending...' : 'Send Reset Email'}
              </button>
              <div className="text-center">
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(false)}
                  className="text-[var(--color-primary)] hover:underline text-sm font-just-sans"
                >
                  Back to Login
                </button>
              </div>
            </form>
            
          )}
          
          <p className="mt-4 text-center font-just-sans text-sm text-[var(--color-text-dark)]">
            Don&apos;t have an account?{' '}
            <a href="/signup" className="text-[var(--color-primary)] hover:underline font-just-sans">Sign up</a>
          </p>
      </div>
    </div>
  );
} 