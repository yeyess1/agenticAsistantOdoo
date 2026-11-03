import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server for the Docker image (U-13): `.next/standalone/server.js`.
  output: "standalone",
};

export default nextConfig;
