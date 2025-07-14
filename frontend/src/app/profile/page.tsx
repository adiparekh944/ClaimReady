'use client';
import { useAuth } from '../../components/AuthContext';

export default function ProfilePage() {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>You are not logged in.</div>;

  return (
    <div style={{ maxWidth: 400, margin: '0 auto', padding: 32 }}>
      <h2>Profile</h2>
      <p><strong>Email:</strong> {user.email}</p>
    </div>
  );
} 