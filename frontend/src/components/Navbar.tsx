'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import Image from 'next/image';

export default function Navbar() {
  const pathname = usePathname();
  
  return (
    <header className="w-full bg-[var(--color-bg-primary)] ">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <Link href="/" className="flex items-center">
            <Image 
              src="/logo2.png" 
              alt="ClaimReady" 
              width={70} 
              height={70} 
              className="mr-2"
            />
          </Link>
          
          <div className="flex items-center space-x-8 font-black-future font-bold">
          <NavLink href="/about" isActive={pathname === "/about"}>
              About
            </NavLink>

            <NavLink href="/upload" isActive={pathname === "/upload"}>
              Upload
            </NavLink>
            
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
      className={`font-medium transition-colors ${
        isActive 
          ? 'text-[var(--color-primary)] border-b-2 border-[var(--color-primary)]' 
          : 'text-white hover:text-[var(--color-primary)]'
      }`}
    >
      {children}
    </Link>
  );
}
