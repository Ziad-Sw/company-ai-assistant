import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    globalNotFound: true,
  },
  // alias الـnext-intl/config → i18n/request.ts — نفس اللي بيействمه
  // createNextIntlPlugin، من غير سحب @swc/core في الـconfig.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
    resolveAlias: {
      "next-intl/config": "./i18n/request.ts",
    },
  },
  webpack: (config) => {
    config.resolve.alias["next-intl/config"] = config.resolve.alias["next-intl/config"] ?? "./i18n/request.ts";
    return config;
  },
  async redirects() {
    return [
      // / (من غير locale) → الإنجليزي الافتراضي — [locale] هو الـroot layout.
      { source: "/", destination: "/en", permanent: false },
    ];
  },
};

export default nextConfig;
