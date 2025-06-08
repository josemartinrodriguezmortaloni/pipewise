import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/integrations/:path*",
        destination: "http://localhost:8001/api/integrations/:path*", // Integrations en debug backend
      },
      {
        source: "/api/calendar/:path*",
        destination: "http://localhost:8001/api/calendar/:path*", // Calendar endpoints en debug backend
      },
      {
        source: "/api/:path*",
        destination: "http://localhost:8001/api/:path*", // Otros endpoints en debug backend
      },
    ];
  },
};

export default nextConfig;
