/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep the Postgres driver external so Next doesn't try to bundle it.
  serverExternalPackages: ["pg"],
};

export default nextConfig;
