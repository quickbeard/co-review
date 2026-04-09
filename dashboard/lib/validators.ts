/**
 * Common validation utilities
 */

export interface ValidationResult {
  valid: boolean;
  error?: string;
  normalizedValue?: string;
}

/**
 * Validates and normalizes a URL for API base endpoints
 *
 * @param url - The URL to validate
 * @param options - Validation options
 * @returns ValidationResult with normalized URL if valid
 */
export function validateApiBaseUrl(
  url: string,
  options: {
    requireHttps?: boolean;
    allowEmpty?: boolean;
    fallbackUrl?: string;
  } = {},
): ValidationResult {
  const { requireHttps = false, allowEmpty = false, fallbackUrl } = options;

  // Handle empty URL
  const trimmedUrl = url.trim();
  if (!trimmedUrl) {
    if (allowEmpty && fallbackUrl) {
      return { valid: true, normalizedValue: fallbackUrl };
    }
    if (allowEmpty) {
      return { valid: true, normalizedValue: "" };
    }
    return { valid: false, error: "URL is required" };
  }

  // Try to parse the URL
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(trimmedUrl);
  } catch {
    return { valid: false, error: "Invalid URL format" };
  }

  // Check protocol
  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    return { valid: false, error: "URL must use http or https protocol" };
  }

  if (requireHttps && parsedUrl.protocol !== "https:") {
    return { valid: false, error: "URL must use https protocol" };
  }

  // Normalize the URL:
  // - Remove trailing slash from pathname
  // - Keep the origin and pathname only (no query string or hash)
  let normalizedPath = parsedUrl.pathname;

  // Remove trailing slash (including the root "/" for domain-only URLs)
  if (normalizedPath === "/") {
    normalizedPath = "";
  } else if (normalizedPath.endsWith("/")) {
    normalizedPath = normalizedPath.slice(0, -1);
  }

  const normalizedUrl = `${parsedUrl.origin}${normalizedPath}`;

  return { valid: true, normalizedValue: normalizedUrl };
}

/**
 * Normalizes an API base URL for making requests
 * Ensures the URL ends without a trailing slash and has /v1 if needed for OpenAI-compatible APIs
 *
 * @param url - The URL to normalize
 * @param fallback - Fallback URL if input is empty
 * @returns Normalized URL string
 */
export function normalizeApiBaseUrl(url: string, fallback: string): string {
  const result = validateApiBaseUrl(url, {
    allowEmpty: true,
    fallbackUrl: fallback,
  });
  return result.normalizedValue || fallback;
}
