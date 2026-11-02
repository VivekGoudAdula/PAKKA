import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Strict mode for React best practices
  reactStrictMode: true,

  // Optimise images (allow local SVGs too)
  images: {
    remotePatterns: [],
  },

  // Export commonly-used environment variables to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000",
  },
};

export default nextConfig;
