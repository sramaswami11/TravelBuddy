import { Link } from 'react-router-dom';

export function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-indigo-900 px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-2xl font-black text-white tracking-tight">
          packed<span className="text-yellow-400">N</span>booked
        </Link>
        <Link to="/" className="text-indigo-300 text-sm hover:text-white transition-colors">
          ← Home
        </Link>
      </header>

      <main className="max-w-3xl mx-auto w-full px-6 py-12 flex-1">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-400 mb-10">Last updated: August 25, 2026</p>

        <div className="prose prose-gray max-w-none space-y-8 text-gray-700 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Overview</h2>
            <p>
              packedNbooked ("we," "us," or "our") operates the website{' '}
              <a href="https://packednbooked.com" className="text-indigo-600 hover:underline">
                packednbooked.com
              </a>{' '}
              (the "Service"). This Privacy Policy explains what information we collect, how we use
              it, and your rights with respect to it.
            </p>
            <p className="mt-3">
              We are committed to protecting your privacy. We do not require you to create an
              account or provide personal information to use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">2. Information We Collect</h2>

            <h3 className="font-semibold text-gray-700 mb-2">Information you provide</h3>
            <p>
              When you perform a trip search, you provide: a departure airport, budget amount, trip
              duration, number of travelers, and an optional departure date. We do not store this
              search data on our servers beyond what is necessary to process your request. No name,
              email address, or payment information is collected or required.
            </p>

            <h3 className="font-semibold text-gray-700 mt-4 mb-2">Automatically collected information</h3>
            <p>
              Like most websites, our servers may automatically receive standard web log information
              when you visit, including your IP address, browser type, operating system, referring
              URL, and pages visited. This information is used in aggregate to monitor service
              performance and is not used to identify individuals.
            </p>

            <h3 className="font-semibold text-gray-700 mt-4 mb-2">Cookies</h3>
            <p>
              We may use cookies or similar technologies to maintain session state and improve
              performance. We do not use cookies for advertising or cross-site tracking. You can
              disable cookies in your browser settings; the Service will continue to function
              without them.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">3. How We Use Your Information</h2>
            <p>We use the information collected to:</p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Process your trip search and return results</li>
              <li>Monitor and improve the performance and reliability of the Service</li>
              <li>Diagnose technical issues</li>
            </ul>
            <p className="mt-3">
              We do not sell, rent, or trade your information to third parties. We do not use your
              search data for advertising purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">4. Affiliate Links & Third-Party Services</h2>
            <p>
              packedNbooked displays results with links to third-party travel booking platforms
              including Booking.com, Skyscanner, Viator, and others. When you click one of these
              links and complete a booking, we may earn an affiliate commission at no additional
              cost to you.
            </p>
            <p className="mt-3">
              These third-party platforms have their own privacy policies and data practices, which
              we do not control. We encourage you to review the privacy policy of any site you visit
              through our links:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>
                <a href="https://www.booking.com/content/privacy.html" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                  Booking.com Privacy Policy
                </a>
              </li>
              <li>
                <a href="https://www.skyscanner.net/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                  Skyscanner Privacy Policy
                </a>
              </li>
              <li>
                <a href="https://www.viator.com/support/privacyPolicy" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                  Viator Privacy Policy
                </a>
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">5. Data Retention</h2>
            <p>
              We do not persistently store your search queries or any personally identifiable
              information. Server logs may be retained for up to 30 days for diagnostic purposes,
              after which they are deleted.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">6. Children's Privacy</h2>
            <p>
              The Service is not directed to children under the age of 13. We do not knowingly
              collect personal information from children. If you believe a child has provided us
              with personal information, please contact us and we will delete it promptly.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">7. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. When we do, we will update the
              "Last updated" date at the top of this page. Continued use of the Service after any
              changes constitutes your acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">8. Contact Us</h2>
            <p>
              If you have questions or concerns about this Privacy Policy, please contact us at:{' '}
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
