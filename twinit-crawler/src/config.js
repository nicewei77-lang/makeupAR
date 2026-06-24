export const config = {
  startUrls: [
    "https://www.twinit.ai/",
    "https://www.twinit.ai/pbv-identity-analysis-engine-ai-agent",
    "https://www.twinit.ai/ai-personal-color-profiling-ai-agent",
    "https://www.twinit.ai/facial-zone-makeup-lab-ai-agent",
    "https://www.twinit.ai/real-texture-ar-simulation-ai-agent",
    "https://www.twinit.ai/skin-profiling-ai-agent",
    "https://www.twinit.ai/customized-skincare-tutorial-ai-agent",
    "https://www.twinit.ai/aging-preview-ai-agent",
    "https://www.twinit.ai/blog",
    "https://www.twinit.ai/contact-us",
  ],

  sitemapSources: [
    "https://www.twinit.ai/sitemap.xml",
    "https://www.twinit.ai/pages-sitemap.xml",
    "https://www.twinit.ai/blog-posts-sitemap.xml",
  ],

  allowedDomains: ["www.twinit.ai"],

  // robots.txt 기반 차단 경로
  robotsDisallow: [
    "?lightbox=",
    "/_partials",
    "/pro-gallery-webapp/",
  ],

  maxDepth: 2,
  crawlDelayMs: 1200,
  concurrency: 1,
  timeoutMs: 60000,

  viewport: { width: 1440, height: 900 },

  userAgent:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 research-crawler-private-study contact:nicewei77@gmail.com",

  outputDir: new URL("../data", import.meta.url).pathname,
};
