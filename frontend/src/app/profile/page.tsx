'use client';
import { useAuth } from '../../components/AuthContext';

export default function ProfilePage() {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>You are not logged in.</div>;

  return (
    <div className="max-w-md w-full mx-auto p-4 sm:p-8 bg-white rounded-lg shadow font-kumbh-sans mt-8">
      <h2 className="text-2xl font-bold mb-4 text-center text-[var(--color-primary)]">Profile</h2>
      <p className="text-lg text-center"><strong>Email:</strong> {user.email}</p>
    </div>
  );
} 