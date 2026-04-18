'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthContext';
import SupabaseGoogleSignInButton from '@/components/SupabaseGoogleSignInButton';
import { ShineBorder } from "@/components/magicui/shine-border";


export default function SignupPage() {
  const { loading, user, signUp, signInAsGuest, signInWithGoogle } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const router = useRouter();

  if (user) {
    router.replace('/');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    const res = await signUp(email, password, username);
    if (res?.error) {
      setError(res.error.message || 'Failed to sign up');
    } else {
      setSuccess('Account created! Check your email to verify.');
    }
  };

  const handleGuest = () => {
    signInAsGuest();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-primary)] font-kumbh-sans">
      
      <div className="w-full max-w-md bg-white rounded-lg p-8 relative overflow-hidden">
        <ShineBorder shineColor={["#ffffff", "#0051ff"]} duration={20} borderWidth={3} />
       
        <h2 className="text-3xl font-just-sans mb-6 text-center text-[var(--color-primary)]">Sign Up</h2>
        
        <div className="mb-6 font-just-sans">
          <SupabaseGoogleSignInButton loading={loading} onClick={async () => { await signInWithGoogle(); }} />
        </div>
        
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500 font-just-sans">or</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 mt-6">
          <div>
            <label className="block text-sm font-just-sans mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              style= {{fontFamily: "var(--font-geist-sans)"}}
              className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              placeholder="Enter your username"
            />
          </div>
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
          <div>
            <label className="block text-sm font-just-sans mb-1">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              style= {{fontFamily: "var(--font-geist-sans)"}}
              placeholder="Confirm your password"
            />
          </div>
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
          {success && <div className="text-green-600 text-sm text-center">{success}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors font-just-sans"
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>
        <div className="mt-6 flex flex-col items-center">
          <span className="text-gray-500 text-sm mb-2 font-just-sans">or</span>
          <button
            type="button"
            onClick={handleGuest}
            className="w-full py-2 px-4 bg-gray-200 text-[var(--color-primary)] rounded-md font-semibold hover:bg-gray-300 transition-colors font-just-sans"
          >
            Try as Guest
          </button>
        </div>
        <p className="mt-4 text-center text-sm font-just-sans">
          Already have an account?{' '}
          <a href="/login" className="text-[var(--color-primary)] hover:underline font-just-sans">Login</a>
        </p>
      </div>
    </div>
  );
} 