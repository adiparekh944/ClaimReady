import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable static optimization
  trailingSlash: false,
  // Disable x-powered-by header
  poweredByHeader: false,
  // Enable compression
  compress: true,
};

export default nextConfig;
