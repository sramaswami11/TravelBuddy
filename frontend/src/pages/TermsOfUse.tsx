import { Link } from 'react-router-dom';

export function TermsOfUse() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-indigo-900 px-6 py-4">
        <Link to="/" className="text-2xl font-black text-white tracking-tight">
          packed<span className="text-yellow-400">N</span>booked
        </Link>
      </header>

      <main className="max-w-3xl mx-auto w-full px-6 py-12 flex-1">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Use</h1>
        <p className="text-sm text-gray-400 mb-10">Last updated: August 25, 2026</p>

        <div className="prose prose-gray max-w-none space-y-8 text-gray-700 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Acceptance of Terms</h2>
            <p>
              By accessing or using packedNbooked at{' '}
              <a href="https://packednbooked.com" className="text-indigo-600 hover:underline">
                packednbooked.com
              </a>{' '}
              (the "Service"), you agree to be bound by these Terms of Use. If you do not agree to
              these terms, please do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">2. Description of Service</h2>
            <p>
              packedNbooked is a trip planning tool that helps users discover travel packages
              (flights, hotels, car rental, and activities) based on a specified budget, travel
              duration, and departure city. Results are generated using real-time flight data and
              AI-assisted ranking, and include affiliate links to third-party booking platforms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">3. Affiliate Disclosure</h2>
            <p>
              packedNbooked participates in affiliate marketing programs. When you click a booking
              link and complete a purchase on a third-party platform (such as Booking.com,
              Skyscanner, or Viator), we may earn a commission. This commission comes at no
              additional cost to you — the price you pay is the same whether or not you use our
              links.
            </p>
            <p className="mt-3">
              This disclosure is made in accordance with the U.S. Federal Trade Commission (FTC)
              guidelines on endorsements and testimonials.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">4. Accuracy of Information</h2>
            <p>
              Flight prices displayed on packedNbooked are estimates sourced from third-party APIs
              and may not reflect current fares at the time of booking. Hotel, car rental, and
              activity prices are illustrative and subject to change. We make no guarantee that
              any price, availability, or itinerary displayed is accurate, current, or achievable.
            </p>
            <p className="mt-3 font-medium text-gray-800">
              Always confirm prices, availability, and total costs directly on the booking
              platform before completing any purchase.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">5. Third-Party Platforms</h2>
            <p>
              The Service links to third-party booking platforms. packedNbooked is not responsible
              for the content, accuracy, policies, or practices of any third-party website. Your
              use of third-party platforms is governed by their own terms of service and privacy
              policies. We strongly recommend reviewing those terms before completing a booking.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">6. No Warranty</h2>
            <p>
              The Service is provided "as is" and "as available" without warranties of any kind,
              either express or implied, including but not limited to warranties of merchantability,
              fitness for a particular purpose, or non-infringement. We do not warrant that the
              Service will be uninterrupted, error-free, or free of viruses or other harmful
              components.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">7. Limitation of Liability</h2>
            <p>
              To the fullest extent permitted by applicable law, packedNbooked shall not be liable
              for any indirect, incidental, special, consequential, or punitive damages arising out
              of or related to your use of the Service, including but not limited to: booking
              errors, price inaccuracies, travel disruptions, or losses resulting from reliance on
              information provided by the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">8. Acceptable Use</h2>
            <p>You agree not to:</p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Use the Service for any unlawful purpose</li>
              <li>Attempt to reverse-engineer, scrape, or systematically extract data from the Service</li>
              <li>Interfere with or disrupt the integrity or performance of the Service</li>
              <li>Use the Service to transmit spam or unsolicited communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">9. Intellectual Property</h2>
            <p>
              All content, design, and code on packedNbooked — including but not limited to the
              brand name, logo, and website design — is the property of packedNbooked and is
              protected by applicable intellectual property laws. You may not reproduce or
              redistribute any part of the Service without prior written permission.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">10. Changes to Terms</h2>
            <p>
              We reserve the right to modify these Terms of Use at any time. Changes will be
              effective upon posting to this page with an updated date. Continued use of the
              Service after changes are posted constitutes your acceptance of the revised terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">11. Governing Law</h2>
            <p>
              These Terms of Use are governed by the laws of the United States. Any disputes
              arising out of or related to these terms or the Service shall be resolved in
              accordance with applicable U.S. law.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">12. Contact Us</h2>
            <p>
              Questions about these Terms of Use? Contact us at:{' '}
              <a href="mailto:hello@packednbooked.com" className="text-indigo-600 hover:underline">
                hello@packednbooked.com
              </a>
            </p>
          </section>

        </div>
      </main>

      <footer className="bg-white border-t border-gray-100 py-6 px-4 mt-auto">
        <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-gray-400">
          <Link to="/" className="font-bold text-gray-600 hover:text-indigo-600 transition-colors">
            packed<span className="text-yellow-500">N</span>booked
          </Link>
          <div className="flex gap-5">
            <Link to="/privacy" className="hover:text-indigo-600 transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-indigo-600 transition-colors">Terms of Use</Link>
            <a href="mailto:hello@packednbooked.com" className="hover:text-indigo-600 transition-colors">Contact</a>
          </div>
          <span>© {new Date().getFullYear()} packedNbooked</span>
        </div>
      </footer>
    </div>
  );
}
