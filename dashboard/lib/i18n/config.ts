export const locales = ["en-US", "vi"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en-US";

export function hasLocale(locale: string): locale is Locale {
  return locales.includes(locale as Locale);
}
