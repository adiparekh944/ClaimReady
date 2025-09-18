'use client';
import { ReactNode } from 'react';
// import { SessionProvider } from 'next-auth/react';
// import { NextAuthProvider } from '../components/NextAuthContext';

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {/* <SessionProvider>
        <NextAuthProvider> */}
          {children}
      {/*   </NextAuthProvider>
      </SessionProvider> */}
    </>
  );
} 