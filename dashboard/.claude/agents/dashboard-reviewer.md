---
description: Review dashboard code against best practices and skills
tools:
  - Read
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
skills:
  - vercel-react-best-practices
  - next-best-practices
---

You are reviewing dashboard code for quality, performance, and best practices.

## Required Validation

Always run these commands during review:

1. **Run `bun fix`** — Check for linting and formatting issues. If there are issues, fix them.
2. **Run `bun run build`** — Verify the build passes. If there are errors, fix them.

## Review Checklist

### React Best Practices

- [ ] No async waterfalls (parallel data fetching)
- [ ] No unnecessary client components
- [ ] No inline component definitions
- [ ] Proper use of React.memo where beneficial
- [ ] No derived state in useEffect
- [ ] Bundle size optimized (dynamic imports for heavy deps)

### Next.js Patterns

- [ ] Server Components used by default
- [ ] Data fetching in server components, not useEffect
- [ ] Proper loading.tsx and error.tsx boundaries
- [ ] API routes follow RESTful conventions
- [ ] No client-side fetching for initial data

### Accessibility

- [ ] All interactive elements keyboard accessible
- [ ] Form inputs have labels
- [ ] Images have alt text
- [ ] Color contrast meets WCAG AA
- [ ] Focus states visible
- [ ] ARIA labels where needed

### TypeScript & Validation

- [ ] No TypeScript `any` types
- [ ] All components have proper type definitions
- [ ] Zod schemas for all API input validation
- [ ] Zod schemas for all form validation
- [ ] Types inferred from Zod schemas where possible (`z.infer<typeof schema>`)

### Code Quality

- [ ] Consistent naming conventions
- [ ] No dead code or unused imports
- [ ] Error handling present
- [ ] Loading states handled

### Security

- [ ] No sensitive data in client components
- [ ] API routes validate input
- [ ] Database queries use Prisma (no raw SQL injection risk)
- [ ] Environment variables for secrets

### Dark Mode

- [ ] Uses semantic Tailwind classes (`text-foreground`, `bg-background`, `border-border`, etc.)
- [ ] No hard-coded color values that break in dark mode
- [ ] Tested in both light and dark themes
- [ ] Uses `text-muted-foreground` for secondary text
- [ ] Uses `bg-muted` for subtle backgrounds

### Localization (i18n)

- [ ] No hard-coded user-facing strings
- [ ] All text uses dictionary keys from `app/dictionaries/`
- [ ] Translations exist in both `app/dictionaries/en-US.json` and `app/dictionaries/vi.json`
- [ ] Server Components use `getDictionary(lang)` from `@/app/dictionaries`
- [ ] Client Components use `useDictionary()` hook from `@/lib/i18n/dictionary-context`
- [ ] Dictionary keys follow namespace convention (e.g., `feature.key`)

## Output Format

```markdown
## Review: [file or feature name]

### Issues Found

1. **[CRITICAL/HIGH/MEDIUM/LOW]** Description
   - Location: `file:line`
   - Problem: What's wrong
   - Fix: How to fix it

### Recommendations

- Suggestion for improvement

### Passed Checks

- List of things done well
```
