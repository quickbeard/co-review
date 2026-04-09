import { describe, it, expect } from "vitest";
import { validateApiBaseUrl, normalizeApiBaseUrl } from "@/lib/validators";

describe("validateApiBaseUrl", () => {
  describe("valid URLs", () => {
    it("should accept valid https URL", () => {
      const result = validateApiBaseUrl("https://api.openai.com/v1");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });

    it("should accept valid http URL", () => {
      const result = validateApiBaseUrl("http://localhost:3000/api");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("http://localhost:3000/api");
    });

    it("should normalize URL with trailing slash", () => {
      const result = validateApiBaseUrl("https://api.openai.com/v1/");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });

    it("should normalize URL with multiple trailing slashes in path", () => {
      const result = validateApiBaseUrl(
        "https://netmind.viettel.vn/gateway/v1/",
      );
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe(
        "https://netmind.viettel.vn/gateway/v1",
      );
    });

    it("should handle URL with only domain", () => {
      const result = validateApiBaseUrl("https://api.openai.com");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com");
    });

    it("should handle URL with port", () => {
      const result = validateApiBaseUrl("http://localhost:11434/v1");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("http://localhost:11434/v1");
    });

    it("should strip query parameters", () => {
      const result = validateApiBaseUrl("https://api.openai.com/v1?key=value");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });

    it("should strip hash fragments", () => {
      const result = validateApiBaseUrl("https://api.openai.com/v1#section");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });

    it("should trim whitespace", () => {
      const result = validateApiBaseUrl("  https://api.openai.com/v1  ");
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });
  });

  describe("invalid URLs", () => {
    it("should reject empty URL when not allowed", () => {
      const result = validateApiBaseUrl("");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("URL is required");
    });

    it("should reject invalid URL format", () => {
      const result = validateApiBaseUrl("not-a-url");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("Invalid URL format");
    });

    it("should reject URL with invalid protocol", () => {
      const result = validateApiBaseUrl("ftp://api.openai.com/v1");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("URL must use http or https protocol");
    });

    it("should reject http when requireHttps is true", () => {
      const result = validateApiBaseUrl("http://api.openai.com/v1", {
        requireHttps: true,
      });
      expect(result.valid).toBe(false);
      expect(result.error).toBe("URL must use https protocol");
    });
  });

  describe("options", () => {
    it("should allow empty URL when allowEmpty is true", () => {
      const result = validateApiBaseUrl("", { allowEmpty: true });
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("");
    });

    it("should use fallback URL when empty and fallback provided", () => {
      const result = validateApiBaseUrl("", {
        allowEmpty: true,
        fallbackUrl: "https://api.openai.com/v1",
      });
      expect(result.valid).toBe(true);
      expect(result.normalizedValue).toBe("https://api.openai.com/v1");
    });

    it("should accept https with requireHttps", () => {
      const result = validateApiBaseUrl("https://api.openai.com/v1", {
        requireHttps: true,
      });
      expect(result.valid).toBe(true);
    });
  });
});

describe("normalizeApiBaseUrl", () => {
  it("should return normalized URL for valid input", () => {
    const result = normalizeApiBaseUrl(
      "https://api.openai.com/v1/",
      "https://fallback.com",
    );
    expect(result).toBe("https://api.openai.com/v1");
  });

  it("should return fallback for empty input", () => {
    const result = normalizeApiBaseUrl("", "https://api.openai.com/v1");
    expect(result).toBe("https://api.openai.com/v1");
  });

  it("should return fallback for whitespace-only input", () => {
    const result = normalizeApiBaseUrl("   ", "https://api.openai.com/v1");
    expect(result).toBe("https://api.openai.com/v1");
  });

  it("should handle netmind URL correctly", () => {
    const result = normalizeApiBaseUrl(
      "https://netmind.viettel.vn/gateway/v1",
      "https://api.openai.com/v1",
    );
    expect(result).toBe("https://netmind.viettel.vn/gateway/v1");
  });
});
