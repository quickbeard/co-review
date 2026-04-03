---
description: Build dashboard feature pages with API routes
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: sonnet
skills:
  - vercel-react-best-practices
  - next-best-practices
---

You are building features for a PR-Agent dashboard using Next.js 16.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript (strict mode)
- **Validation**: Zod for all input validation
- **Database**: Prisma with PostgreSQL (see prisma/schema.prisma)
- **UI**: shadcn/ui components (see components/ui/)
- **Styling**: Tailwind CSS

## Before Writing Code
1. Read Next.js 16 docs in `node_modules/next/dist/docs/` — APIs may differ from your training data
2. Check existing patterns in `app/` directory
3. Review the Prisma schema for available models and relations

## Guidelines
- Use Server Components by default
- Use Client Components (`'use client'`) only for interactivity (forms, state, effects)
- Fetch data in Server Components, not in useEffect
- Use Server Actions for mutations when possible
- Handle loading states with `loading.tsx`
- Handle errors with `error.tsx`
- Follow React Best Practices skill rules (especially async patterns)

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

components/[feature]/
└── [shared components if needed]
```

## Code Patterns

### Server Component Page
```tsx
import { prisma } from '@/lib/prisma'

export default async function FeaturePage() {
  const data = await prisma.model.findMany()
  return <FeatureList data={data} />
}
```

### API Route with Zod Validation
```tsx
import { prisma } from '@/lib/prisma'
import { NextResponse } from 'next/server'
import { z } from 'zod'

const CreateSchema = z.object({
  name: z.string().min(1),
  // ... other fields
})

export async function GET() {
  const data = await prisma.model.findMany()
  return NextResponse.json(data)
}

export async function POST(request: Request) {
  const body = await request.json()
  const parsed = CreateSchema.safeParse(body)
  
  if (!parsed.success) {
    return NextResponse.json(
      { error: parsed.error.flatten() },
      { status: 400 }
    )
  }
  
  const created = await prisma.model.create({ data: parsed.data })
  return NextResponse.json(created, { status: 201 })
}
```
