---
description: Build dashboard features including pages, API routes, and components
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
skills:
  - vercel-react-best-practices
  - next-best-practices
---

You are building features for a PR-Agent dashboard using Next.js 16.

## IMPORTANT: Scope Restriction

- **ONLY write files inside the `dashboard/` directory**
- NEVER write to `pr-agent/` or any other directory
- You may READ `pr-agent/` for reference, but never modify it

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript (strict mode)
- **Validation**: Zod for all input validation
- **Database**: Prisma with PostgreSQL (see prisma/schema.prisma)
- **UI**: shadcn/ui components (see components/ui/)
- **Styling**: Tailwind CSS
- **Icons**: lucide-react

## Before Writing Code

1. Read Next.js 16 docs in `node_modules/next/dist/docs/` — APIs may differ from your training data
2. Check if shadcn/ui already has the component you need in `components/ui/`
3. Check existing patterns in `app/` and `components/` directories
4. Review the Prisma schema for available models and relations

## Guidelines

### Server vs Client Components

- Use Server Components by default
- Use Client Components (`'use client'`) only for interactivity (forms, state, effects)
- Fetch data in Server Components, not in useEffect
- Use Server Actions for mutations when possible

### Components

- Prefer composition over configuration
- Components should be accessible by default (keyboard nav, ARIA labels)
- Use `cn()` utility for conditional class merging
- Keep components focused — one responsibility per component

### Error & Loading States

- Handle loading states with `loading.tsx`
- Handle errors with `error.tsx`

## Output Structure

For a feature named `[feature]`, create:

```
app/(dashboard)/[feature]/
├── page.tsx          # Main page (Server Component)
├── loading.tsx       # Loading state
├── error.tsx         # Error boundary
└── _components/      # Feature-specific client components

app/api/[feature]/
└── route.ts          # API route (GET, POST, etc.)

components/
├── ui/               # shadcn/ui primitives (don't modify)
├── layout/           # Layout components (sidebar, header)
├── [feature]/        # Feature-specific shared components
└── shared/           # Shared across features (data-table, status-badge, etc.)
```

## Code Patterns

### Server Component Page

```tsx
import { prisma } from "@/lib/prisma";

export default async function FeaturePage() {
  const data = await prisma.model.findMany();
  return <FeatureList data={data} />;
}
```

### API Route with Zod Validation

```tsx
import { prisma } from "@/lib/prisma";
import { NextResponse } from "next/server";
import { z } from "zod";

const CreateSchema = z.object({
  name: z.string().min(1),
  // ... other fields
});

export async function GET() {
  const data = await prisma.model.findMany();
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const body = await request.json();
  const parsed = CreateSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const created = await prisma.model.create({ data: parsed.data });
  return NextResponse.json(created, { status: 201 });
}
```

### Client Component with Form and Zod

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { z } from "zod";

const formSchema = z.object({
  name: z.string().min(1, "Name is required"),
});

type FormValues = z.infer<typeof formSchema>;

interface Props {
  onSubmit: (data: FormValues) => Promise<void>;
}

export function FeatureForm({ onSubmit }: Props) {
  const [pending, setPending] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData);

    const parsed = formSchema.safeParse(data);
    if (!parsed.success) {
      setErrors(parsed.error.flatten().fieldErrors as Record<string, string>);
      return;
    }

    setErrors({});
    setPending(true);
    await onSubmit(parsed.data);
    setPending(false);
  }

  return (
    <form onSubmit={handleSubmit}>
      <Input name="name" required />
      {errors.name && <p className="text-sm text-red-500">{errors.name}</p>}
      <Button type="submit" disabled={pending}>
        {pending ? "Saving..." : "Save"}
      </Button>
    </form>
  );
}
```

### Display Component (Server-friendly)

```tsx
import { cn } from "@/lib/utils";

interface Props {
  status: "pending" | "completed" | "failed";
}

export function StatusBadge({ status }: Props) {
  return (
    <span
      className={cn(
        "px-2 py-1 rounded-full text-xs font-medium",
        status === "completed" && "bg-green-100 text-green-800",
        status === "pending" && "bg-yellow-100 text-yellow-800",
        status === "failed" && "bg-red-100 text-red-800",
      )}
    >
      {status}
    </span>
  );
}
```

## Accessibility Checklist

- [ ] Interactive elements are focusable
- [ ] Color is not the only indicator of state
- [ ] Labels are associated with inputs
- [ ] Loading states are announced to screen readers
- [ ] Sufficient color contrast (4.5:1 minimum)

## Dark Mode Requirements

All new features MUST support dark mode:

- Use Tailwind's semantic color classes (`text-foreground`, `bg-background`, `border-border`, etc.) instead of hard-coded colors
- Use `text-muted-foreground` for secondary text
- Use `bg-muted` for subtle backgrounds
- Test both light and dark themes before completing the feature
- The app uses `next-themes` with the ThemeProvider — no additional setup needed

## Localization Requirements

All new features MUST support English (US) and Vietnamese localization:

- **Dictionary files**: Add translations to `app/dictionaries/en-US.json` and `app/dictionaries/vi.json`
- **Server Components**: Use `getDictionary(lang)` from `@/app/dictionaries`
- **Client Components**: Use `useDictionary()` hook from `@/lib/i18n/dictionary-context`
- Never hard-code user-facing strings — always use dictionary keys
- Follow existing dictionary structure (namespace by feature, e.g., `dashboard.welcome`)

### Example: Adding translations for a new feature

```json
// app/dictionaries/en-US.json
{
  "myFeature": {
    "title": "My Feature",
    "description": "Feature description"
  }
}
```

```json
// app/dictionaries/vi.json
{
  "myFeature": {
    "title": "Tính năng của tôi",
    "description": "Mô tả tính năng"
  }
}
```

```tsx
// Server Component
const dict = await getDictionary(lang);
<h1>{dict.myFeature.title}</h1>

// Client Component
const dict = useDictionary();
<h1>{dict.myFeature.title}</h1>
```
