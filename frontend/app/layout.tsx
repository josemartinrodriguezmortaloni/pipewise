import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";
import { AuthProvider } from "@/hooks/use-auth";
import "./globals.css";

// Modern font loading with display optimization
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
  preload: true,
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
  preload: false, // Only preload primary font
});

// Enhanced metadata with modern SEO
export const metadata: Metadata = {
  title: {
    default: "PipeWise - Modern B2B SaaS Platform",
    template: "%s | PipeWise",
  },
  description:
    "Modern B2B SaaS platform with OpenAI AgentSDK, multi-tenant architecture, and advanced lead management",
  keywords: ["CRM", "SaaS", "B2B", "Lead Management", "AI", "Multi-tenant"],
  authors: [{ name: "PipeWise Team" }],
  creator: "PipeWise",
  publisher: "PipeWise",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://pipewise.com",
    siteName: "PipeWise",
    title: "PipeWise - Modern B2B SaaS Platform",
    description:
      "Modern B2B SaaS platform with OpenAI AgentSDK and multi-tenant architecture",
  },
  twitter: {
    card: "summary_large_image",
    title: "PipeWise - Modern B2B SaaS Platform",
    description:
      "Modern B2B SaaS platform with OpenAI AgentSDK and multi-tenant architecture",
  },
  manifest: "/manifest.json",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
};

// Modern viewport configuration
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
  ],
};

// Root Layout as Server Component with React 19 optimizations
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable}`}
      suppressHydrationWarning={true}
    >
      <head>
        {/* DNS prefetch for external resources */}
        <link rel="dns-prefetch" href="//fonts.googleapis.com" />
        <link rel="dns-prefetch" href="//api.pipewise.com" />

        {/* Preconnect for critical resources */}
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />

        {/* Critical resource hints */}
        <link rel="modulepreload" href="/_next/static/chunks/app/layout.js" />
      </head>
      <body className="antialiased font-sans bg-background text-foreground">
        {/* Main application with error boundary */}
        <div id="root" className="min-h-screen">
          <AuthProvider>
            {/* Main content area */}
            <main className="relative">{children}</main>

            {/* Global toast notifications */}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: "hsl(var(--background))",
                  color: "hsl(var(--foreground))",
                  border: "1px solid hsl(var(--border))",
                },
              }}
            />
          </AuthProvider>
        </div>

        {/* Portal container for modals */}
        <div id="portal-root" />

        {/* Skip to main content for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-primary text-primary-foreground px-4 py-2 rounded z-50"
        >
          Skip to main content
        </a>
      </body>
    </html>
  );
}
