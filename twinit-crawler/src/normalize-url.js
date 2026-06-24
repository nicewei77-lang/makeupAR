import { config } from "./config.js";

/**
 * URL을 정규화한다. hash·불필요한 query 제거, trailing slash 통일, https 강제.
 * @param {string} raw - 정규화할 URL (상대/절대 모두 허용)
 * @param {string} [base] - 상대 URL 해석 기준
 * @returns {string|null} 정규화된 URL, 또는 처리 불가일 때 null
 */
export function normalizeUrl(raw, base) {
  if (!raw || typeof raw !== "string") return null;

  const trimmed = raw.trim();

  // 비 http 스킴 제외
  if (/^(mailto:|tel:|javascript:|#)/i.test(trimmed)) return null;

  let url;
  try {
    url = new URL(trimmed, base || undefined);
  } catch {
    return null;
  }

  // https 강제
  url.protocol = "https:";

  // hash 제거
  url.hash = "";

  // 불필요한 query 제거 (lightbox 포함 파라미터)
  const allowedParams = new Set([]); // 허용 파라미터 없음(전량 제거)
  for (const key of [...url.searchParams.keys()]) {
    if (!allowedParams.has(key)) url.searchParams.delete(key);
  }

  // trailing slash 통일: path가 /로 끝나고 확장자 없으면 slash 제거
  if (url.pathname.endsWith("/") && url.pathname !== "/") {
    url.pathname = url.pathname.replace(/\/$/, "");
  }

  return url.href;
}

/**
 * URL이 허용된 내부 도메인에 속하는지 확인한다.
 */
export function isInternalUrl(url) {
  try {
    const { hostname } = new URL(url);
    return config.allowedDomains.includes(hostname);
  } catch {
    return false;
  }
}

/**
 * robots.txt Disallow 규칙에 해당하는 URL인지 확인한다.
 */
export function isRobotsBlocked(url) {
  return config.robotsDisallow.some((pattern) => url.includes(pattern));
}

/**
 * URL에서 파일명용 slug를 생성한다.
 * https://www.twinit.ai/real-texture-ar-simulation-ai-agent → real-texture-ar-simulation-ai-agent
 * 한글/유니코드 경로는 디코딩 후 로마자 음역 없이 그대로 사용하되 안전한 문자만 남긴다.
 */
export function slugifyUrl(url) {
  try {
    const { pathname } = new URL(url);
    // percent-decode 후 슬래시를 _로 치환
    const decoded = decodeURIComponent(pathname).replace(/^\//, "").replace(/\//g, "_") || "home";
    // 안전한 파일명 문자(영문·숫자·한글·_·-)만 허용, 나머지는 -로 치환, 연속 -는 하나로
    return decoded
      .replace(/[^\w가-힣\-]/g, "-")
      .replace(/-{2,}/g, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase()
      .slice(0, 80);
  } catch {
    return "unknown";
  }
}
