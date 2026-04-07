import "server-only";
import type { Locale } from "@/lib/i18n/config";

const dictionaries = {
  "en-US": () =>
    import("./dictionaries/en-US.json").then((module) => module.default),
  vi: () => import("./dictionaries/vi.json").then((module) => module.default),
};

export const getDictionary = async (locale: Locale) => dictionaries[locale]();

export type Dictionary = Awaited<ReturnType<typeof getDictionary>>;
