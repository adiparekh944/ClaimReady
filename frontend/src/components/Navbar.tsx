'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from './AuthContext';

export default function Navbar() {
  const pathname = usePathname();
  const { user, signOut, loading } = useAuth();
  
  return (
    <header className="w-full sticky top-0 z-50 backdrop-blur-sm">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <Link href="/" className="flex items-center">
            <Image 
              src="/logo.png" 
              alt="ClaimReady" 
              width={60} 
              height={60} 
              className="mr-2"
            />
            <span className="text-2xl font-bold text-[var(--color-primary)] font-clash-display-semibold">ClaimReady</span>
          </Link>
          
          <div className="flex items-center space-x-8 font-kumbh-sans font-bold text-lg">
          {/*<NavLink href="/about" isActive={pathname === "/about"}>
              About
            </NavLink>*/}

            <NavLink href="/" isActive={pathname === "/"}>
              Home
            </NavLink>

            <NavLink href="/upload" isActive={pathname === "/upload"}>
              Upload
            </NavLink>
            {/* User menu */}
            {!loading && !user && (
              <NavLink href="/login" isActive={pathname === "/login"}>
                Login
              </NavLink>
            )}
            {!loading && user && (
              <>
                <NavLink href="/profile" isActive={pathname === "/profile"}>
                  Profile
                </NavLink>
                <button onClick={signOut} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit' }}>
                  Logout
                </button>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}

interface NavLinkProps {
  href: string;
  isActive: boolean;
  children: React.ReactNode;
}

function NavLink({ href, isActive, children }: NavLinkProps) {
  return (
    <Link 
      href={href} 
      className={`font-medium transition-colors text-base md:text-lg ${
        isActive 
          ? 'text-[var(--color-text-primary)] border-b-2 border-[var(--color-primary)]' 
          : 'text-[var(--color-text-primary)] hover:text-[var(--color-primary)]'
      }`}
    >
      {children}
    </Link>
  );
}
