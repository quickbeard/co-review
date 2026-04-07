import { vi } from "vitest";

// Mock next/cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

// Mock the database
vi.mock("@/lib/db", () => ({
  prisma: {
    organization: {
      findFirst: vi.fn(),
      create: vi.fn(),
    },
    gitProvider: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      findFirst: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}));
