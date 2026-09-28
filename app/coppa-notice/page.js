// Public COPPA notice page — no sign-in required.
// Starting point, not legal advice; needs a licensed attorney's review before
// going beyond family and friends.

export const metadata = {
  title: 'Privacy & COPPA Notice — MathCompete',
  description: 'How MathCompete collects and uses information about your child, and your rights under COPPA.',
}

const SUPPORT_EMAIL = 'kalyanashisc86+mathcompete@gmail.com'

export default function CoppaNoticePage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <div className="max-w-3xl mx-auto px-5 py-10 md:py-14">
        <a href="/" className="text-indigo-600 font-semibold text-sm">&larr; Back to MathCompete</a>

        <h1 className="mt-6 text-3xl md:text-4xl font-extrabold font-display text-slate-900">
          MathCompete — COPPA Notice to Parents
        </h1>

        <p className="mt-5 leading-relaxed">
          MathCompete is a math practice app for kids in grades 1–5, used through a parent&apos;s account.
          This notice explains what MathCompete collects about your child, why, and what rights you have
          under the Children&apos;s Online Privacy Protection Act (COPPA).
        </p>

        <Section title="Who creates the account">
          <p>
            Only a parent (or another verified adult) signs in to MathCompete, using Google Sign-In.
            Access is currently invite-only: only email addresses added to the account&apos;s allowlist can
            sign in at all. A child never signs in directly, never provides an email address, and never
            creates their own login.
          </p>
        </Section>

        <Section title="What we collect about your child">
          <p>Once you&apos;re signed in, you create a profile for each child by providing only:</p>
          <ul className="list-disc pl-6 mt-2 space-y-1">
            <li>Your child&apos;s first name or nickname</li>
            <li>Their grade level (1 through 5)</li>
          </ul>
          <p className="mt-3">
            From there, MathCompete stores what your child does in the app: the avatar and theme they
            select, and their gameplay activity — which practice sessions they&apos;ve completed, their
            answers, scores, streaks, and stars earned.
          </p>
          <p className="mt-3">
            MathCompete does not collect your child&apos;s email address, birthdate, photo, location, or any
            contact information. Your child never fills out a form or creates an account of their own —
            everything is set up by you, the parent.
          </p>
        </Section>

        <Section title="How we use this information">
          <p>
            Only to run the app for your family: showing grade-appropriate problems, tracking your
            child&apos;s own progress, and letting you see how they&apos;re doing. We do not use your child&apos;s
            information for advertising, do not build marketing profiles from it, and do not sell it.
          </p>
        </Section>

        <Section title="Who we share it with">
          <p>
            We don&apos;t share your child&apos;s information with third parties. MathCompete uses an AI service
            (Anthropic) only to help write new practice questions offline, before they&apos;re ever added to
            the app — it never sees your child&apos;s personal data, answers, or activity.
          </p>
        </Section>

        <Section title="Your rights as a parent">
          <p>You can, at any time:</p>
          <ul className="list-disc pl-6 mt-2 space-y-1">
            <li>Ask us what&apos;s stored for your child (contact below).</li>
            <li>
              Ask us to delete your account and every child profile under it — email{' '}
              <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-600 font-semibold break-all">{SUPPORT_EMAIL}</a>{' '}
              and we&apos;ll remove it.
            </li>
            <li>Stop further collection by deleting the account.</li>
          </ul>
        </Section>

        <Section title="How long we keep it">
          <p>
            We keep your child&apos;s information as long as your account is active. If you ask us to delete
            your account, we permanently delete your child&apos;s information within a reasonable time of your
            request, except anything we&apos;re legally required to keep.
          </p>
        </Section>

        <Section title="Where it's stored">
          <p>
            In a secured database (MongoDB Atlas), accessible only through your authenticated parent
            session.
          </p>
        </Section>

        <Section title="Questions or concerns">
          <p>
            Contact us at{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-indigo-600 font-semibold break-all">{SUPPORT_EMAIL}</a>{' '}
            with any questions about this notice or your child&apos;s information.
          </p>
        </Section>
      </div>
    </main>
  )
}

function Section({ title, children }) {
  return (
    <section className="mt-8">
      <h2 className="text-xl md:text-2xl font-extrabold font-display text-slate-900">{title}</h2>
      <div className="mt-2 leading-relaxed text-slate-700">{children}</div>
    </section>
  )
}
