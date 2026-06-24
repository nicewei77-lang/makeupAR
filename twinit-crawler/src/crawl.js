import { chromium } from "playwright";
import { existsSync } from "fs";
import { writeFile, readFile, appendFile } from "fs/promises";
import path from "path";
import * as cheerio from "cheerio";
import { config } from "./config.js";
import { normalizeUrl, isInternalUrl, isRobotsBlocked, slugifyUrl } from "./normalize-url.js";
import { extractPageData } from "./extract.js";

// ───────────────────────── 로거 ─────────────────────────
const logPath = path.join(config.outputDir, "logs", "crawl.log");
const errPath = path.join(config.outputDir, "logs", "errors.jsonl");

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  appendFile(logPath, line + "\n").catch(() => {});
}

async function logError(url, error) {
  const entry = JSON.stringify({ url, error: error.message, ts: new Date().toISOString() });
  await appendFile(errPath, entry + "\n").catch(() => {});
  log(`ERROR ${url}: ${error.message}`);
}

// ─────────────────── sitemap 파싱 ───────────────────────
async function fetchSitemapUrls(page) {
  const found = new Set();
  for (const sitemapUrl of config.sitemapSources) {
    try {
      const resp = await page.request.get(sitemapUrl, { timeout: 15000 });
      if (!resp.ok()) continue;
      const xml = await resp.text();
      const $ = cheerio.load(xml, { xmlMode: true });

      // 인덱스 사이트맵 (<sitemapindex>) 처리
      $("sitemap loc").each((_, el) => {
        const u = $(el).text().trim();
        const n = normalizeUrl(u);
        if (n && isInternalUrl(n) && !isRobotsBlocked(n)) found.add(n);
      });

      // 일반 사이트맵 (<urlset>) 처리
      $("url loc").each((_, el) => {
        const u = $(el).text().trim();
        const n = normalizeUrl(u);
        if (n && isInternalUrl(n) && !isRobotsBlocked(n)) found.add(n);
      });

      log(`sitemap ${sitemapUrl}: ${found.size} URLs 누적`);
    } catch (err) {
      log(`sitemap 파싱 실패 ${sitemapUrl}: ${err.message}`);
    }
  }
  return [...found];
}

// ─────────────────── 페이지 렌더링 ──────────────────────
async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 400;
      const timer = setInterval(() => {
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= document.body.scrollHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 150);
    });
  });
  // 맨 위로 복귀 (full-page screenshot 보정)
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function crawlPage(page, url, depth) {
  log(`크롤링 시작 [depth:${depth}] ${url}`);

  let status = 0;
  try {
    // Wix 사이트는 networkidle이 오지 않으므로 load 후 추가 대기
    const resp = await page.goto(url, {
      waitUntil: "load",
      timeout: config.timeoutMs,
    });
    await page.waitForTimeout(2500);
    status = resp?.status() ?? 0;

    if (status >= 400) {
      await logError(url, new Error(`HTTP ${status}`));
      return null;
    }

    // lazy-load 이미지 위해 자동 스크롤
    await autoScroll(page);

    const slug = slugifyUrl(url);
    const crawled_at = new Date().toISOString();

    // HTML 저장
    const htmlPath = path.join(config.outputDir, "raw_html", `${slug}.html`);
    const htmlContent = await page.evaluate(() => document.documentElement.outerHTML);
    await writeFile(htmlPath, htmlContent, "utf8");

    // 스크린샷 저장
    const screenshotPath = path.join(config.outputDir, "screenshots", `${slug}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    // 데이터 추출
    const data = await extractPageData(page, url);

    // Markdown 저장
    const mdPath = path.join(config.outputDir, "markdown", `${slug}.md`);
    await writeFile(mdPath, data.markdown, "utf8");

    // pages.jsonl 행 생성
    const pageRecord = {
      url,
      slug,
      title: data.title,
      crawled_at,
      language: data.language,
      depth,
      status,
      html_path: `data/raw_html/${slug}.html`,
      screenshot_path: `data/screenshots/${slug}.png`,
      markdown_path: `data/markdown/${slug}.md`,
      headings: data.headings,
      visible_text: data.visible_text.slice(0, 2000),
      internal_links: data.internal_links.map((l) => l.url),
      external_links: data.external_links.map((l) => l.url),
      metrics: data.metrics,
      image_count: data.image_count,
      content_hash: data.content_hash,
    };

    await appendFile(
      path.join(config.outputDir, "jsonl", "pages.jsonl"),
      JSON.stringify(pageRecord) + "\n"
    );

    // links.jsonl
    for (const link of data.internal_links) {
      const linkRecord = {
        source_url: url,
        target_url: link.url,
        type: "internal",
        anchor_text: link.anchor_text,
      };
      await appendFile(
        path.join(config.outputDir, "jsonl", "links.jsonl"),
        JSON.stringify(linkRecord) + "\n"
      );
    }
    for (const link of data.external_links) {
      const linkRecord = {
        source_url: url,
        target_url: link.url,
        type: "external",
        anchor_text: link.anchor_text,
      };
      await appendFile(
        path.join(config.outputDir, "jsonl", "links.jsonl"),
        JSON.stringify(linkRecord) + "\n"
      );
    }

    // images.jsonl
    for (const img of data.images) {
      await appendFile(
        path.join(config.outputDir, "jsonl", "images.jsonl"),
        JSON.stringify({ page_url: url, ...img }) + "\n"
      );
    }

    log(`완료 [${status}] ${url} → slug:${slug}, images:${data.image_count}`);

    return {
      newInternalUrls: data.internal_links.map((l) => l.url),
    };
  } catch (err) {
    await logError(url, err);
    return null;
  }
}

// ───────────────────── delay ──────────────────────────────
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

// ───────────────────── 메인 ──────────────────────────────
async function main() {
  log("=== Twinit 크롤러 시작 ===");

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: config.userAgent,
    viewport: config.viewport,
  });
  const page = await context.newPage();

  // sitemap에서 추가 URL 수집
  const sitemapUrls = await fetchSitemapUrls(page);
  log(`sitemap에서 발견된 URL: ${sitemapUrls.length}개`);

  // seed + sitemap 합산, 중복 제거
  const allSeeds = new Set([...config.startUrls, ...sitemapUrls].map((u) => normalizeUrl(u)).filter(Boolean));

  const visited = new Set();
  // { url, depth } 형식의 큐
  const queue = [...allSeeds].map((u) => ({ url: u, depth: 0 }));

  while (queue.length > 0) {
    const { url, depth } = queue.shift();

    if (visited.has(url)) continue;
    if (!isInternalUrl(url)) continue;
    if (isRobotsBlocked(url)) {
      log(`robots 차단 스킵: ${url}`);
      continue;
    }
    if (depth > config.maxDepth) continue;

    // XML 파일, 에셋, API 경로는 크롤 대상에서 제외
    if (/\.(xml|json|rss|atom|css|js|png|jpg|jpeg|gif|svg|ico|woff|ttf)$/i.test(url)) {
      log(`비HTML 파일 스킵: ${url}`);
      continue;
    }

    visited.add(url);

    // 이미 수집된 파일이 있으면 스킵 (재실행 안전)
    const slug = slugifyUrl(url);
    const htmlPath = path.join(config.outputDir, "raw_html", `${slug}.html`);
    if (existsSync(htmlPath)) {
      log(`이미 수집됨 스킵: ${url}`);
      continue;
    }

    const result = await crawlPage(page, url, depth);

    if (result && depth < config.maxDepth) {
      for (const nextUrl of result.newInternalUrls) {
        const norm = normalizeUrl(nextUrl);
        if (norm && !visited.has(norm) && isInternalUrl(norm) && !isRobotsBlocked(norm)) {
          queue.push({ url: norm, depth: depth + 1 });
        }
      }
    }

    // 사이트 부하 최소화
    if (queue.length > 0) await delay(config.crawlDelayMs);
  }

  await browser.close();
  log(`=== 크롤링 완료: 총 ${visited.size}개 페이지 ===`);
}

main().catch((err) => {
  console.error("크롤러 치명적 오류:", err);
  process.exit(1);
});
