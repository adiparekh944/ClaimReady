'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from './AuthContext';
import { useState } from 'react';
import ProfileCard from './ProfileCard';

export default function Navbar() {
  const pathname = usePathname();
  const { user, signOut, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileCardOpen, setProfileCardOpen] = useState(false);

  return (
    <>
      <header className="w-full sticky top-0 z-50 backdrop-blur-lg">
        <div className="container mx-auto px-4 py-3 md:py-4">
          <nav className="flex items-center justify-between">
            <Link href="/" className="flex items-center min-w-0">
              <Image 
                src="/logo.png" 
                alt="ClaimReady" 
                width={48} 
                height={48} 
                className="mr-2 w-10 h-10 md:w-15 md:h-15"
              />
              <span className="truncate text-xl md:text-2xl font-bold text-[var(--color-primary)] font-clash-display-semibold">ClaimReady</span>
            </Link>

            {/* Hamburger menu for mobile */}
            <button
              className="md:hidden ml-2 p-2 rounded focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label="Toggle navigation menu"
            >
              <svg className="w-7 h-7" fill="none" stroke="black" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Desktop navigation */}
            <div className="hidden md:flex items-center space-x-6 font-kumbh-sans font-bold text-base md:text-lg">
              <NavLinks 
                pathname={pathname} 
                user={user} 
                loading={loading} 
                signOut={signOut}
                onProfileClick={() => setProfileCardOpen(true)}
              />
            </div>
          </nav>
          {/* Mobile nav dropdown */}
          {menuOpen && (
            <div className="md:hidden mt-2 bg-[var(--color-bg-primary)] rounded-lg shadow-lg py-2 px-4 absolute right-4 top-16 min-w-[60vw] z-50 border border-gray-200">
              <NavLinks 
                pathname={pathname} 
                user={user} 
                loading={loading} 
                signOut={signOut}
                onClickLink={() => setMenuOpen(false)}
                onProfileClick={() => {
                  setProfileCardOpen(true);
                  setMenuOpen(false);
                }}
              />
            </div>
          )}
        </div>
      </header>
      
      <ProfileCard 
        isOpen={profileCardOpen} 
        onClose={() => setProfileCardOpen(false)} 
      />
    </>
  );
}

function NavLinks({ 
  pathname, 
  user, 
  loading, 
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  signOut, 
  onClickLink, 
  onProfileClick
}: { 
  pathname: string, 
  user: any, 
  loading: boolean, 
  signOut: () => void, 
  onClickLink?: () => void,
  onProfileClick?: () => void
}) {
  return (
    <>
      <NavLink href="/" isActive={pathname === "/"} onClick={onClickLink}>
        Home
      </NavLink>
      <NavLink href="/upload" isActive={pathname === "/upload"} onClick={onClickLink}>
        Upload
      </NavLink>

      <a
        href="https://docs.google.com/forms/d/e/1FAIpQLSfVhrsspIc3hnk8cIASKW1NnUqI5BYRJSdoCVC6X3uol_tG4A/viewform?usp=dialog"
        target="_blank"
        rel="noopener noreferrer"
        onClick={onClickLink}
        className="text-black"
      >
        Contact Us
      </a>
      
      {/* User menu */}
      {!loading && !user && (
        <>
          <NavLink href="/login" isActive={pathname === "/login"} onClick={onClickLink}>
            Login
          </NavLink>
          <NavLink href="/signup" isActive={pathname === "/signup"} onClick={onClickLink}>
            Sign Up
          </NavLink>
        </>
      )}
      {!loading && user && (
        <>
          <button
            onClick={onProfileClick}
            className="ml-2 text-[var(--color-primary)] hover:underline font-medium text-base md:text-lg py-1 px-2 rounded flex items-center"
          >
            <div className="w-8 h-8 bg-[var(--color-primary)] rounded-full flex items-center justify-center text-white font-bold text-sm mr-2">
              {(user.user_metadata?.username?.charAt(0) || user.email?.charAt(0) || 'U').toUpperCase()}
            </div>
            Profile
          </button>
        </>
      )}
    </>
  );
}

interface NavLinkProps {
  href: string;
  isActive: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}

function NavLink({ href, isActive, children, onClick }: NavLinkProps) {
  return (
    <Link 
      href={href} 
      onClick={onClick}
      className={`block font-medium transition-colors text-base md:text-lg py-2 md:py-0 px-2 md:px-0 rounded md:rounded-none ${
        isActive 
          ? 'text-[var(--color-text-dark)] border-b-2 border-[var(--color-primary)] md:border-b-0 md:border-b-2 md:border-[var(--color-primary)]' 
          : 'text-black hover:text-black'
      }`}
    >
      {children}
    </Link>
  );
}
