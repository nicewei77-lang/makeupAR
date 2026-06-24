/**
 * feature-matrix.js — 6-A 기계 단계
 *
 * pages.jsonl을 읽어 feature_matrix.csv의 빈 골격을 생성하고,
 * 수치 지표(+14%, ×3 등)는 자동으로 채운다.
 * AI/AR 주장, relevance 같은 주관 컬럼은 비워서 사람/LLM(classify.js)이 채우게 한다.
 */

import { readFile, writeFile } from "fs/promises";
import { existsSync } from "fs";
import path from "path";
import { config } from "./config.js";

const JSONL_PATH = path.join(config.outputDir, "jsonl", "pages.jsonl");
const CSV_PATH = path.join(config.outputDir, "csv", "feature_matrix.csv");
const INVENTORY_PATH = path.join(config.outputDir, "csv", "page_inventory.csv");

// URL 경로로부터 솔루션 카테고리를 단순 매핑
const CATEGORY_MAP = {
  "pbv-identity-analysis-engine": "AI Makeup",
  "ai-personal-color-profiling": "AI Makeup",
  "facial-zone-makeup-lab": "AI Makeup",
  "real-texture-ar-simulation": "AI Makeup",
  "skin-profiling": "AI Skincare",
  "customized-skincare-tutorial": "AI Skincare",
  "aging-preview": "AI Skincare",
  blog: "Case Study",
  "contact-us": "Contact",
};

function inferCategory(url) {
  for (const [key, cat] of Object.entries(CATEGORY_MAP)) {
    if (url.includes(key)) return cat;
  }
  if (url === "https://www.twinit.ai" || url === "https://www.twinit.ai/") return "Homepage";
  if (url.includes("/post/")) return "Case Study";
  return "Other";
}

// CSV 셀 이스케이프
function csvCell(val) {
  if (val === null || val === undefined) return "";
  const str = String(val);
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function csvRow(cells) {
  return cells.map(csvCell).join(",");
}

async function main() {
  if (!existsSync(JSONL_PATH)) {
    console.error(`pages.jsonl 없음: ${JSONL_PATH}\n先 crawl.js를 실행하세요.`);
    process.exit(1);
  }

  const raw = await readFile(JSONL_PATH, "utf8");
  const pages = raw
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));

  console.log(`페이지 수: ${pages.length}`);

  // ── feature_matrix.csv ─────────────────────────────────
  const matrixHeaders = [
    "page",
    "url",
    "solution_category",
    "metrics_extracted",      // 자동 추출
    // 아래는 LLM/사람이 채우는 컬럼 (비워 둠)
    "feature",
    "input_data",
    "output",
    "ai_claim",
    "ar_claim",
    "business_claim",
    "relevance_to_our_project",
    "notes",
  ];

  const matrixRows = [matrixHeaders.join(",")];

  for (const p of pages) {
    const category = inferCategory(p.url);
    const metrics = (p.metrics || []).join("; ");

    matrixRows.push(
      csvRow([
        p.slug || "",
        p.url || "",
        category,
        metrics,
        "", // feature — 사람/LLM
        "", // input_data
        "", // output
        "", // ai_claim
        "", // ar_claim
        "", // business_claim
        "", // relevance_to_our_project
        "", // notes
      ])
    );
  }

  await writeFile(CSV_PATH, matrixRows.join("\n"), "utf8");
  console.log(`feature_matrix.csv 저장: ${CSV_PATH}`);

  // ── page_inventory.csv ─────────────────────────────────
  const inventoryHeaders = [
    "slug",
    "url",
    "title",
    "language",
    "depth",
    "status",
    "image_count",
    "internal_link_count",
    "external_link_count",
    "metrics",
    "crawled_at",
  ];

  const inventoryRows = [inventoryHeaders.join(",")];
  for (const p of pages) {
    inventoryRows.push(
      csvRow([
        p.slug,
        p.url,
        p.title,
        p.language,
        p.depth,
        p.status,
        p.image_count,
        (p.internal_links || []).length,
        (p.external_links || []).length,
        (p.metrics || []).join("; "),
        p.crawled_at,
      ])
    );
  }

  await writeFile(INVENTORY_PATH, inventoryRows.join("\n"), "utf8");
  console.log(`page_inventory.csv 저장: ${INVENTORY_PATH}`);

  console.log("\n다음 단계: classify.js (LLM/사람)로 feature_matrix.csv의 빈 컬럼을 채우세요.");
}

main().catch((err) => {
  console.error("feature-matrix 오류:", err);
  process.exit(1);
});
