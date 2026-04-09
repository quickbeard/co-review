"use client";

import { useEffect } from "react";

interface LangUpdaterProps {
  lang: string;
}

export function LangUpdater({ lang }: LangUpdaterProps) {
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  return null;
}
