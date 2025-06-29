import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Modern Next.js 15 optimizations (stable features only)
  experimental: {
    // Only include stable experimental features
    optimizePackageImports: ["lucide-react", "@radix-ui/react-icons"],
  },

  // Turbopack is now stable in Next.js 15, but configuration is via CLI only

  // Compiler optimizations
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === "production",
  },

  // Modern output mode for deployment
  output: "standalone",

  // API rewrites to our FastAPI backend
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8001/api/:path*", // Proxy to FastAPI backend
      },
    ];
  },

  // Security and performance headers
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
        ],
      },
      {
        source: "/api/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, must-revalidate",
          },
        ],
      },
    ];
  },

  // Modern image optimization
  images: {
    formats: ["image/avif", "image/webp"],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
    minimumCacheTTL: 60,
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },

  // Performance optimizations
  poweredByHeader: false,
  trailingSlash: false,
  generateEtags: true,

  // Enable compression
  compress: true,

  // TypeScript configuration
  typescript: {
    // Keep TypeScript checks but ignore build errors for now
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    // Disable ESLint during builds temporarily
    ignoreDuringBuilds: true,
  },

  // Suppress the 'self is not defined' warnings during build
  onDemandEntries: {
    // Keep pages in memory for 60 seconds
    maxInactiveAge: 60 * 1000,
    // Number of pages that should be kept simultaneously
    pagesBufferLength: 5,
  },
};

export default nextConfig;
