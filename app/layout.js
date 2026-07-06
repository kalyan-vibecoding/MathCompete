import './globals.css'
import Script from 'next/script'
import { Providers } from './providers'

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
    <html lang="en">
      <body>
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" />
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
