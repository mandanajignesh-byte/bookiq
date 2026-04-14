/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'books.toscrape.com' },
      { protocol: 'https', hostname: 'covers.openlibrary.org' },
    ],
  },
}

module.exports = nextConfig
