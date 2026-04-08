<!-- BEGIN:nextjs-agent-rules -->

# Dashboard Development Guidelines

You are building features for a PR-Agent dashboard using Next.js 16.

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript (strict mode)
- **Validation**: Zod v4 (use `.issues` not `.errors` for error access)
- **UI**: shadcn/ui components built on **Base UI** (NOT Radix) - see components/ui/
- **Styling**: Tailwind CSS
- **Icons**: lucide-react
- **API Client**: Fetch to PR-Agent backend (`lib/api/`)

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

## After Writing Code

Always run these commands after completing a feature:

1. **Run `bun fix`** — Fix linting and formatting issues
2. **Run `bun test:e2e`** — Run e2e tests
3. **Run `bun run build`** — Verify the build passes

## Project Structure

```
dashboard/
├── app/
│   ├── [lang]/              # i18n route segment
│   │   ├── (dashboard)/     # Dashboard layout group
│   │   │   ├── git-providers/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   └── dictionaries/        # i18n JSON files
├── components/
│   ├── ui/                  # shadcn/ui primitives (Base UI)
│   ├── layout/              # Layout components
│   └── git-providers/       # Feature components
├── lib/
│   ├── api/                 # API client for PR-Agent
│   ├── i18n/                # i18n utilities
│   └── utils.ts
└── e2e/                     # Playwright tests
```

## API Integration

Dashboard calls PR-Agent backend via REST API:

```typescript
// lib/api/git-providers.ts
const API_BASE_URL =
  process.env.NEXT_PUBLIC_PR_AGENT_API_URL || "http://localhost:3001";

export async function getGitProviders(): Promise<ApiResponse<GitProvider[]>> {
  const response = await fetch(`${API_BASE_URL}/api/providers`);
  // ...
}
```

## Localization Requirements

All new features MUST support English (US) and Vietnamese:

- **Dictionary files**: `app/dictionaries/en-US.json` and `app/dictionaries/vi.json`
- **Server Components**: Use `getDictionary(lang)` from `@/app/dictionaries`
- **Client Components**: Use `useDictionary()` hook from `@/lib/i18n/dictionary-context`
- Never hard-code user-facing strings

## Dark Mode Requirements

Use Tailwind's semantic color classes:

- `text-foreground`, `bg-background`, `border-border`
- `text-muted-foreground` for secondary text
- `bg-muted` for subtle backgrounds

<!-- END:nextjs-agent-rules -->
