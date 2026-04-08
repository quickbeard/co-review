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
  - .agents/skills/vercel-react-best-practices
  - .agents/skills/next-best-practices
---

You are building features for a PR-Agent dashboard using Next.js 16.

## IMPORTANT: Scope Restriction

- **ONLY write files inside the `dashboard/` directory**
- NEVER write to `pr-agent/` or any other directory
- You may READ `pr-agent/` for reference, but never modify it

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript (strict mode)
- **Validation**: Zod v4 (use `.issues` not `.errors` for error access)
- **Database**: Prisma 7 with PostgreSQL (see prisma/schema.prisma)
- **UI**: shadcn/ui components built on **Base UI** (NOT Radix) - see components/ui/
- **Styling**: Tailwind CSS
- **Icons**: lucide-react

## Base UI Notes (IMPORTANT)

The UI components use `@base-ui/react`, not Radix UI. Key differences:

- **No `asChild` prop** - Base UI triggers render their own elements
- **Different component APIs** - Always check component props in `components/ui/`
- **SSR considerations** - Some components (Select, Dialog) may need `dynamic = "force-dynamic"` on pages to avoid build errors

Example - Dropdown trigger (Base UI style):

```tsx
// Correct - Base UI
<DropdownMenuTrigger className="...">
  <Icon />
</DropdownMenuTrigger>

// Wrong - Radix style (won't work)
<DropdownMenuTrigger asChild>
  <Button><Icon /></Button>
</DropdownMenuTrigger>
```

## Before Writing Code

1. Read Next.js 16 docs in `node_modules/next/dist/docs/` — APIs may differ from your training data
2. Check if shadcn/ui already has the component you need in `components/ui/`
3. Check existing patterns in `app/` and `components/` directories
4. Review the Prisma schema for available models and relations

## After Writing Code

Always run these commands after completing a feature:

1. **Run `bun fix`** — Fix linting and formatting issues. If there are errors, fix them before proceeding.
2. **Run `bun test:run`** — Run unit tests. If there are failures, fix them.
3. **Run `bun test:e2e`** — Run e2e tests. If there are failures, fix them.
4. **Run `bun run build`** — Verify the build passes. If there are errors, fix them.

## Unit Testing

Use **Vitest** for unit testing. Write tests for server actions and utility functions.

### When to Write Tests

- **Always test**: Server actions (`lib/actions/*.ts`), utility functions, complex business logic
- **Skip tests for**: Simple UI components, pages that just fetch and render data

### Test Structure

```
tests/
├── setup.ts                    # Global mocks (Prisma, Next.js)
└── lib/
    └── actions/
        └── [feature].test.ts   # Tests for server actions
```

### Example Test for Server Actions

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { prisma } from "@/lib/db";
import { createItem, getItems } from "@/lib/actions/items";

// Mock Prisma
vi.mock("@/lib/db", () => ({
  prisma: {
    item: {
      findMany: vi.fn(),
      create: vi.fn(),
    },
  },
}));

// Mock next/cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

describe("Item Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should create an item with valid data", async () => {
    vi.mocked(prisma.item.create).mockResolvedValue({ id: "1", name: "Test" });

    const formData = new FormData();
    formData.append("name", "Test");

    const result = await createItem(formData);

    expect(result.success).toBe(true);
    expect(prisma.item.create).toHaveBeenCalled();
  });

  it("should return error for invalid data", async () => {
    const formData = new FormData();
    formData.append("name", ""); // Invalid - empty

    const result = await createItem(formData);

    expect(result.success).toBe(false);
  });
});
```

### Running Tests

```bash
bun test:run        # Single run
bun test:coverage   # With coverage report
```

## E2E Testing

Use **Playwright** for end-to-end testing. Write e2e tests for user-facing features after building them.

### When to Write E2E Tests

- **Always test**: New pages, critical user flows (forms, navigation, CRUD operations)
- **Skip tests for**: Internal refactors, API-only routes, non-user-facing changes

### Test Structure

```
e2e/
└── [feature].spec.ts   # E2E tests for feature
```

### Example E2E Test

```typescript
import { test, expect } from "@playwright/test";

test.describe("Feature Name", () => {
  test("should display feature page", async ({ page }) => {
    await page.goto("/en-US/feature");

    // Use specific selectors to avoid strict mode violations
    await expect(
      page.getByRole("heading", { name: "Feature Title", level: 1 }),
    ).toBeVisible();
  });

  test("should navigate to create page", async ({ page }) => {
    await page.goto("/en-US/feature");

    // Use .first() if multiple matching elements exist
    await page.getByRole("link", { name: /add/i }).first().click();

    await expect(page).toHaveURL(/\/feature\/new/);
  });

  test("should show form validation", async ({ page }) => {
    await page.goto("/en-US/feature/new");

    await page.getByRole("button", { name: /create/i }).click();

    // Check for validation feedback
    const input = page.getByLabel(/name/i);
    await expect(input).toBeVisible();
  });

  test("should interact with select dropdown", async ({ page }) => {
    await page.goto("/en-US/feature/new");

    // Open select and choose option
    await page.getByRole("combobox").click();
    await expect(page.getByRole("option", { name: /option/i })).toBeVisible();
  });
});
```

### E2E Testing Tips

- **Use specific selectors**: Prefer `{ level: 1 }` for headings, `.first()` for duplicate elements
- **Use locale prefix**: Always use `/en-US/` prefix in URLs for consistent testing
- **Avoid timeouts**: If elements don't appear, check for SSR issues (add `export const dynamic = "force-dynamic"` to page)
- **Test real flows**: Focus on what users actually do, not implementation details

### Running E2E Tests

```bash
bun test:e2e      # Run e2e tests (Firefox only, configured in playwright.config.ts)
bun test:e2e:ui   # Interactive UI mode
```

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
    // Zod v4 uses .issues, not .errors
    return NextResponse.json(
      { error: parsed.error.issues[0]?.message ?? "Invalid data" },
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
      // Zod v4: convert issues array to field errors
      const fieldErrors: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const field = issue.path[0]?.toString();
        if (field && !fieldErrors[field]) {
          fieldErrors[field] = issue.message;
        }
      }
      setErrors(fieldErrors);
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
<h1>{dict.myFeature.title}</h1>;

// Client Component
const dict = useDictionary();
<h1>{dict.myFeature.title}</h1>;
```
