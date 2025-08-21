'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../components/AuthContext';
import { BorderBeam } from '@/components/magicui/border-beam';
export default function SignupPage() {
  const { signUp, loading, user, signInAsGuest } = useAuth();
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

    const result = await signUp(email, password, username);
    if (result?.error) {
      setError(result.error.message || 'Signup failed');
    } else {
      setSuccess('Account created successfully! Please check your email to verify your account.');
    }
  };

  const handleGuest = () => {
    signInAsGuest();
    router.replace('/upload');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-dark)] font-kumbh-sans">
      
      <div className="w-full max-w-md bg-white rounded-lg shadow-[0_0_40px_var(--shadow-color-primary)] p-8 relative overflow-hidden">
        <span className="pointer-events-none absolute inset-0 rounded-lg">
          <BorderBeam duration={8} size={400} borderWidth={2.5} colorFrom="var(--color-primary)" colorTo="var(--color-primary-dark)" />
        </span>
        <h2 className="text-3xl font-bold mb-6 text-center text-[var(--color-primary)]">Sign Up</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              placeholder="Enter your username"
            />
          </div>
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
          <div>
            <label className="block text-sm font-medium mb-1">Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              placeholder="Confirm your password"
            />
          </div>
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
          {success && <div className="text-green-600 text-sm text-center">{success}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-[var(--color-primary)] text-white rounded-md font-semibold hover:bg-[var(--color-primary-dark)] transition-colors"
          >
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>
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
        <p className="mt-4 text-center text-sm">
          Already have an account?{' '}
          <a href="/login" className="text-[var(--color-primary)] hover:underline">Login</a>
        </p>
      </div>
    </div>
  );
} 