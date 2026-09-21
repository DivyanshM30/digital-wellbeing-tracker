/** @type {import('next').NextConfig} */
const nextConfig = {
  // Vercel uses the native Next.js build; export only for generic static hosts.
  ...(process.env.NEXT_STATIC_EXPORT === "1" ? { output: "export" } : {}),
  trailingSlash: true,
  devIndicators: false,
};

export default nextConfig;
