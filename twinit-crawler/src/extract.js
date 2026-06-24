import * as cheerio from "cheerio";
import TurndownService from "turndown";
import { normalizeUrl, isInternalUrl, isRobotsBlocked } from "./normalize-url.js";
import { createHash } from "crypto";

const td = new TurndownService({
  headingStyle: "atx",
  bulletListMarker: "-",
  codeBlockStyle: "fenced",
});

// 불필요한 노이즈 태그 제거 규칙
td.remove(["script", "style", "noscript", "iframe", "svg"]);

/**
 * Playwright page 객체에서 페이지 데이터를 추출한다.
 * @param {import('playwright').Page} page
 * @param {string} url - 현재 페이지 URL
 * @returns {Promise<object>} 추출된 페이지 데이터
 */
export async function extractPageData(page, url) {
  const html = await page.evaluate(() => document.documentElement.outerHTML);
  const $ = cheerio.load(html);

  const title = $("title").first().text().trim() || $("h1").first().text().trim();
  const metaDescription = $('meta[name="description"]').attr("content")?.trim() || "";
  const lang = $("html").attr("lang") || detectLanguage(title + metaDescription);

  // headings
  const headings = [];
  $("h1, h2, h3, h4, h5, h6").each((_, el) => {
    const text = $(el).text().trim();
    if (text) headings.push({ level: Number(el.tagName[1]), text });
  });

  // visible text (노이즈 제거 후)
  const $clone = cheerio.load(html);
  $clone("script, style, noscript, iframe, nav, footer, header").remove();
  const visibleText = $clone("body").text().replace(/\s+/g, " ").trim().slice(0, 8000);

  // links
  const internalLinks = [];
  const externalLinks = [];
  $("a[href]").each((_, el) => {
    const href = $(el).attr("href");
    const anchor = $(el).text().trim().slice(0, 200);
    const normalized = normalizeUrl(href, url);
    if (!normalized) return;
    if (isRobotsBlocked(normalized)) return;

    const entry = { url: normalized, anchor_text: anchor };
    if (isInternalUrl(normalized)) internalLinks.push(entry);
    else externalLinks.push(entry);
  });

  // images
  const images = [];
  $("img[src], img[data-src]").each((_, el) => {
    const src = $(el).attr("src") || $(el).attr("data-src");
    const alt = $(el).attr("alt")?.trim() || "";
    if (src && !src.startsWith("data:")) images.push({ src, alt });
  });

  // CTA 버튼 텍스트
  const ctaTexts = [];
  $("button, a.btn, [class*='cta'], [class*='button']").each((_, el) => {
    const text = $(el).text().trim();
    if (text && text.length < 100) ctaTexts.push(text);
  });

  // 수치 지표 추출 (+14%, ×3, 67% 등)
  const metricsPattern = /([+×x]?\d+(?:\.\d+)?[%배x×]|\d+(?:\.\d+)?배)/g;
  const metrics = [...new Set((visibleText.match(metricsPattern) || []))];

  // Markdown 변환
  const cleanHtml = removeNoise(html);
  const markdown = buildMarkdown({ url, title, metaDescription, headings, visibleText, internalLinks, externalLinks, images, ctaTexts });

  const contentHash = createHash("sha256").update(html).digest("hex");

  return {
    url,
    title,
    meta_description: metaDescription,
    language: lang,
    headings,
    visible_text: visibleText,
    internal_links: dedupeLinks(internalLinks),
    external_links: dedupeLinks(externalLinks),
    images: images.slice(0, 50),
    cta_texts: [...new Set(ctaTexts)].slice(0, 20),
    metrics,
    image_count: images.length,
    content_hash: contentHash,
    markdown,
  };
}

function detectLanguage(text) {
  const koChars = (text.match(/[가-힣]/g) || []).length;
  return koChars > 5 ? "ko" : "en";
}

function removeNoise(html) {
  const $ = cheerio.load(html);
  $("script, style, noscript, iframe, svg, nav, footer, header").remove();
  return $.html();
}

function dedupeLinks(links) {
  const seen = new Set();
  return links.filter(({ url }) => {
    if (seen.has(url)) return false;
    seen.add(url);
    return true;
  });
}

function buildMarkdown({ url, title, metaDescription, headings, visibleText, internalLinks, externalLinks, images, ctaTexts }) {
  const now = new Date().toISOString();

  const hSection = headings
    .map(({ level, text }) => `${"#".repeat(level + 1)} ${text}`)
    .join("\n");

  const iLinkSection = internalLinks
    .slice(0, 30)
    .map(({ url: u, anchor_text }) => `- [${anchor_text || u}](${u})`)
    .join("\n");

  const eLinkSection = externalLinks
    .slice(0, 30)
    .map(({ url: u, anchor_text }) => `- [${anchor_text || u}](${u})`)
    .join("\n");

  const imgSection = images
    .slice(0, 20)
    .map(({ src, alt }) => `- ![${alt}](${src})`)
    .join("\n");

  const ctaSection = ctaTexts.slice(0, 10).map((t) => `- ${t}`).join("\n");

  return `# ${title}

## Page Metadata

- URL: ${url}
- Crawled At: ${now}
- Title: ${title}
- Meta Description: ${metaDescription}

## Headings

${hSection || "(없음)"}

## Visible Text

${visibleText}

## CTA / Buttons

${ctaSection || "(없음)"}

## Internal Links

${iLinkSection || "(없음)"}

## External Links

${eLinkSection || "(없음)"}

## Images

${imgSection || "(없음)"}
`;
}
