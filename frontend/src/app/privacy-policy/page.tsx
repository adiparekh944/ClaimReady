'use client';

import Navbar from "@/components/Navbar";
import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <div className="relative min-h-screen bg-[var(--color-bg-dark)]">
      <Navbar />
      <main className="relative z-10 bg-[var(--color-bg-dark)] pt-20">
        <div className="container mx-auto px-4 py-12">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold text-[var(--color-primary)] font-clash-display-semibold mb-8 text-center">
              Privacy Policy
            </h1>
            
            <div className="bg-[var(--color-bg-primary)] rounded-lg p-8 shadow-lg">
              <div className="prose prose-invert max-w-none">
                <p className="text-[var(--color-text-secondary)] mb-6 font-kumbh-sans">
                  <strong>Last updated:</strong> {new Date().toLocaleDateString()}
                </p>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    1. Information We Collect
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      <strong>Personal Information:</strong> When you use ClaimReady, we may collect personal information such as your name, email address, and contact information when you create an account or contact us.
                    </p>
                    <p>
                      <strong>Usage Data:</strong> We collect information about how you use our service, including the features you use, the content you upload, and your interactions with our platform.
                    </p>
                    <p>
                      <strong>Device Information:</strong> We may collect information about your device, including your IP address, browser type, and operating system.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    2. How We Use Your Information
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>We use the information we collect to:</p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Provide and maintain our services</li>
                      <li>Process your claims and provide valuations</li>
                      <li>Improve our services and develop new features</li>
                      <li>Communicate with you about our services</li>
                      <li>Ensure the security and integrity of our platform</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    3. Information Sharing
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We do not sell, trade, or otherwise transfer your personal information to third parties without your consent, except in the following circumstances:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>With your explicit consent</li>
                      <li>To comply with legal obligations</li>
                      <li>To protect our rights and safety</li>
                      <li>With service providers who assist in operating our platform</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    4. Data Security
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We implement appropriate security measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. However, no method of transmission over the internet is 100% secure.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    5. Your Rights
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>You have the right to:</p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Access your personal information</li>
                      <li>Correct inaccurate information</li>
                      <li>Request deletion of your information</li>
                      <li>Opt-out of certain communications</li>
                      <li>Lodge a complaint with supervisory authorities</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    6. Cookies and Tracking
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We use cookies and similar tracking technologies to enhance your experience on our platform. You can control cookie settings through your browser preferences.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    7. Changes to This Policy
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new policy on this page and updating the &ldquoLast updated&ldquo date.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    8. Contact Us
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      If you have any questions about this Privacy Policy, please contact us at:
                    </p>
                    <div className="bg-[var(--color-bg-dark)] p-4 rounded-lg">
                      <p className="font-semibold">ClaimReady</p>
                      <p>Email: adityaparekh944@gmail.com</p>
                      <p>Website: useclaimready.ai</p>
                    </div>
                  </div>
                </section>
              </div>
            </div>

            <div className="text-center mt-8">
              <Link 
                href="/"
                className="inline-flex items-center px-6 py-3 bg-[var(--color-primary)] text-white rounded-lg hover:bg-[var(--color-primary-dark)] transition-colors font-kumbh-sans font-semibold"
              >
                ← Back to Home
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
