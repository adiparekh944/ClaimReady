import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Inter, JetBrains_Mono,} from 'next/font/google';
import localFont from 'next/font/local';
import ClientLayout from './ClientLayout';

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

// Adding Clash Display Semibold font
const clashDisplaySemibold = localFont({
  src: '../../public/fonts/ClashDisplay-Semibold.otf',
  variable: '--font-clash-display-semibold',
  display: 'swap',
  preload: true
});

const justSans = localFont({
  src: '../../public/fonts/JustSans.otf', 
  variable: '--font-just-sans',
  display: 'swap',
  preload: true

})


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

const reglo = localFont({
  src: [
    {
      path: "../../public/fonts/reglo.bold.otf",
      weight: "700",
      style: "normal",
    },
  ],
  variable: "--font-reglo",
  display: "swap",
  preload: true,
});

const youngSerif = localFont({
  src: [
    {
      path: "../../public/fonts/YoungSerif-Regular.ttf",
      weight: "400",
      style: "normal",
    },
  ],
  variable: "--font-young-serif",
  display: "swap",
  preload: true,
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        suppressHydrationWarning={true}
        className={`${geistSans.variable} ${geistMono.variable} ${inter.className} ${jetbrainsMono.className} ${francy.variable} ${blackFuture.variable} ${KumbhSans.variable} ${clashDisplaySemibold.variable} ${reglo.variable} ${youngSerif.variable} ${justSans.variable}`}
      >
        <ClientLayout>
          {children}
        </ClientLayout>
      </body>
    </html>
  );
}
