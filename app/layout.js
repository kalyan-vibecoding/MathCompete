import './globals.css'
import Script from 'next/script'
import { Fredoka, Lexend } from 'next/font/google'
import { Providers } from './providers'

// Self-hosted at build time (served from our own domain) — no runtime request to
// Google's servers, so no visitor IP is sent to Google. Same families & weights.
const lexend = Lexend({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-lexend',
  display: 'swap',
})
const fredoka = Fredoka({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-fredoka',
  display: 'swap',
})

export const metadata = {
  title: 'MathCompete \u2014 Daily Math Game',
  description: 'A daily set of 30 math problems styled as a game for kids in grades 1\u20135.',
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${lexend.variable} ${fredoka.variable}`}>
      <body>
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
