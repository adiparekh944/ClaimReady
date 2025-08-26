'use client';

import Navbar from "@/components/Navbar";
import Link from "next/link";

export default function TermsOfServicePage() {
  return (
    <div className="relative min-h-screen bg-[var(--color-bg-dark)]">
      <Navbar />
      <main className="relative z-10 bg-[var(--color-bg-dark)] pt-20">
        <div className="container mx-auto px-4 py-12">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold text-[var(--color-primary)] font-clash-display-semibold mb-8 text-center">
              Terms of Service
            </h1>
            
            <div className="bg-[var(--color-bg-primary)] rounded-lg p-8 shadow-lg">
              <div className="prose prose-invert max-w-none">
                <p className="text-[var(--color-text-secondary)] mb-6 font-kumbh-sans">
                  <strong>Last updated:</strong> {new Date().toLocaleDateString()}
                </p>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    1. Acceptance of Terms
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      By accessing and using ClaimReady ("the Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    2. Description of Service
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      ClaimReady is an AI-powered platform that helps users scan, value, and protect their belongings through automated object detection and valuation services. Our service includes:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Image and video analysis for object detection</li>
                      <li>Automated valuation estimates</li>
                      <li>Claims processing assistance</li>
                      <li>Document generation and management</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    3. User Accounts
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      To access certain features of the Service, you may be required to create an account. You are responsible for:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Maintaining the confidentiality of your account credentials</li>
                      <li>All activities that occur under your account</li>
                      <li>Providing accurate and complete information</li>
                      <li>Notifying us immediately of any unauthorized use</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    4. Acceptable Use
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>You agree not to use the Service to:</p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Upload illegal, harmful, or inappropriate content</li>
                      <li>Violate any applicable laws or regulations</li>
                      <li>Infringe on intellectual property rights</li>
                      <li>Attempt to gain unauthorized access to our systems</li>
                      <li>Interfere with the proper functioning of the Service</li>
                    </ul>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    5. Intellectual Property
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      The Service and its original content, features, and functionality are owned by ClaimReady and are protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
                    </p>
                    <p>
                      You retain ownership of content you upload, but grant us a license to use it for providing the Service.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    6. Disclaimers
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      <strong>Valuation Estimates:</strong> Our AI-generated valuations are estimates only and should not be considered as professional appraisals. Actual values may vary significantly.
                    </p>
                    <p>
                      <strong>Service Availability:</strong> The Service is provided "as is" without warranties of any kind. We do not guarantee uninterrupted or error-free operation.
                    </p>
                    <p>
                      <strong>Accuracy:</strong> While we strive for accuracy, we cannot guarantee that all object detections or valuations will be 100% accurate.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    7. Limitation of Liability
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      In no event shall ClaimReady be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    8. Privacy and Data
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      Your privacy is important to us. Please review our Privacy Policy, which also governs your use of the Service, to understand our practices.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    9. Termination
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We may terminate or suspend your account and access to the Service immediately, without prior notice, for any reason, including breach of these Terms.
                    </p>
                    <p>
                      You may terminate your account at any time by contacting us or deleting your account through the Service.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    10. Changes to Terms
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      We reserve the right to modify these Terms at any time. We will notify users of any material changes by posting the new Terms on this page and updating the "Last updated" date.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    11. Governing Law
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      These Terms shall be governed by and construed in accordance with the laws of the jurisdiction in which ClaimReady operates, without regard to its conflict of law provisions.
                    </p>
                  </div>
                </section>

                <section className="mb-8">
                  <h2 className="text-2xl font-bold text-[var(--color-primary)] mb-4 font-clash-display-semibold">
                    12. Contact Information
                  </h2>
                  <div className="text-[var(--color-text-secondary)] font-kumbh-sans space-y-3">
                    <p>
                      If you have any questions about these Terms of Service, please contact us at:
                    </p>
                    <div className="bg-[var(--color-bg-dark)] p-4 rounded-lg">
                      <p className="font-semibold">ClaimReady</p>
                      <p>Email: sohamkundu2704@gmail.com</p>
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
