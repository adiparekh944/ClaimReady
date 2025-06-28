import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Inter, JetBrains_Mono, Poppins } from 'next/font/google';
import localFont from 'next/font/local';

const francy = localFont({
  src: '../../public/fonts/Francy.otf',
  variable: '--font-francy'
});

// Adding Black Future font
const blackFuture = localFont({
  src: '../../public/fonts/Black Future.otf',
  variable: '--font-black-future'
});

const KumbhSans = localFont({
   src: '../../public/fonts/KumbhSans-Bold.ttf',
   variable: '--font-kumbh-sans'
});


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const inter = Inter({ subsets: ['latin'] });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: "ClaimReady",
  description: "Scan, Value, and Protect your belongings.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        suppressHydrationWarning
        className={`${francy.variable} ${blackFuture.variable} ${KumbhSans.variable} ${geistSans.variable} ${geistMono.variable} ${inter.className} ${jetbrainsMono}`}
      >
        {children}
      </body>
    </html>
  );
}
