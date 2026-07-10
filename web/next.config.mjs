/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export → served from the Cloudflare Worker's assets binding.
  // The API lives on the same origin under /api/*, handled by the Worker.
  output: "export",
  images: {
    // No image-optimizer server in a static export.
    unoptimized: true,
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
};

export default nextConfig;
