'use client';
import { useState } from 'react';
import { useAuth } from './AuthContext';
import { useRouter } from 'next/navigation';

interface ProfileCardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ProfileCard({ isOpen, onClose }: ProfileCardProps) {
  const { user, signOut, loading } = useAuth();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const router = useRouter();

  if (!isOpen || !user) return null;

  const handleSignOut = async () => {
    setIsSigningOut(true);
    await signOut();
    setIsSigningOut(false);
    onClose();
    router.replace('/');
  };

  const username = user.user_metadata?.username || 'User';
  const email = user.email || 'No email';
  const createdAt = user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 font-kumbh-sans">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-[var(--color-primary)]">Profile</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-[var(--color-primary)] rounded-full flex items-center justify-center text-white font-bold text-lg">
              {username.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-semibold text-gray-900">{username}</p>
              <p className="text-sm text-gray-600">{email}</p>
            </div>
          </div>
          
          <div className="border-t pt-4 space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Member since:</span>
              <span className="text-sm font-medium">{createdAt}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Account status:</span>
              <span className="text-sm font-medium text-green-600">
                {user.email_confirmed_at ? 'Verified' : 'Pending'}
              </span>
            </div>
          </div>
          
          <div className="border-t pt-4">
            <button
              onClick={handleSignOut}
              disabled={isSigningOut || loading}
              className="w-full py-2 px-4 bg-red-600 text-white rounded-md font-semibold hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              {isSigningOut ? 'Signing out...' : 'Sign Out'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 