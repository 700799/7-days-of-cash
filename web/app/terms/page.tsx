import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms",
  description: "Terms of use for Best7DaysMula.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <main className="prose">
      <h1>&gt; TERMS OF USE</h1>

      <h2>Acceptance</h2>
      <p>
        By accessing Best7DaysMula, you agree to these terms. If you do not agree, do not
        use the site.
      </p>

      <h2>License</h2>
      <p>
        The Best7DaysMula source code is released under the MIT License. You may inspect,
        copy, modify, and self-host the software subject to that license. The hosted site
        and its underlying data are provided as a courtesy at no cost and may be changed,
        rate-limited, or discontinued at any time without notice.
      </p>

      <h2>No warranty</h2>
      <p>
        The site is provided "as is" and "as available" without warranties of any kind,
        express or implied. We do not warrant that the service will be uninterrupted, free
        of errors, secure, accurate, or fit for any particular purpose.
      </p>

      <h2>Limitation of liability</h2>
      <p>
        To the maximum extent permitted by law, the operators of this site shall not be
        liable for any direct, indirect, incidental, special, consequential, or punitive
        damages, including loss of profits, data, or other intangible losses, arising from
        your use of, or inability to use, the site.
      </p>

      <h2>Acceptable use</h2>
      <p>
        Do not abuse the service: no automated scraping at high frequency, no attempts to
        circumvent security controls, and no use that violates applicable law. We may block
        access at our discretion to preserve service quality.
      </p>

      <h2>Not financial advice</h2>
      <p>
        See the <a href="/disclaimer">Disclaimer</a>. Nothing on this site is investment,
        legal, tax, or other professional advice.
      </p>

      <h2>Changes</h2>
      <p>
        These terms may be updated from time to time. Continued use after changes
        constitutes acceptance.
      </p>
    </main>
  );
}
