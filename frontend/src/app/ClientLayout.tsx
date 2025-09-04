'use client';
import { ReactNode } from 'react';
import { SupabaseAuthProvider } from '../components/SupabaseAuthContext';

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <SupabaseAuthProvider>
      {children}
    </SupabaseAuthProvider>
  );
} 