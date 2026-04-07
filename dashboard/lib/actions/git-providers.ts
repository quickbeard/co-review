"use server";

import { prisma } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import type { GitProviderType } from "@/generated/prisma/client";

// =============================================================================
// Schemas
// =============================================================================

const gitProviderTypeValues = [
  "github",
  "gitlab",
  "bitbucket",
  "azure_devops",
  "gitea",
  "gerrit",
] as const;

const createGitProviderSchema = z.object({
  type: z.enum(gitProviderTypeValues),
  name: z.string().min(1, "Name is required").max(100),
  baseUrl: z
    .string()
    .url("Must be a valid URL")
    .optional()
    .or(z.literal(""))
    .transform((val) => val || null),
  accessToken: z.string().min(1, "Access token is required"),
  webhookSecret: z
    .string()
    .optional()
    .transform((val) => val || null),
});

const updateGitProviderSchema = z.object({
  id: z.string().min(1),
  type: z.enum(gitProviderTypeValues),
  name: z.string().min(1, "Name is required").max(100),
  baseUrl: z
    .string()
    .url("Must be a valid URL")
    .optional()
    .or(z.literal(""))
    .transform((val) => val || null),
  accessToken: z.string().optional(),
  webhookSecret: z
    .string()
    .optional()
    .transform((val) => val || null),
});

// =============================================================================
// Types
// =============================================================================

export type GitProviderFormData = z.infer<typeof createGitProviderSchema>;
export type GitProviderUpdateData = z.infer<typeof updateGitProviderSchema>;

export type ActionResult<T = void> =
  | { success: true; data: T }
  | { success: false; error: string; fieldErrors?: Record<string, string> };

// =============================================================================
// Helper Functions
// =============================================================================

async function getOrCreateDefaultOrganization() {
  const existing = await prisma.organization.findUnique({
    where: { slug: "default" },
  });

  if (existing) {
    return existing;
  }

  return prisma.organization.create({
    data: {
      name: "Default Organization",
      slug: "default",
    },
  });
}

// =============================================================================
// Actions
// =============================================================================

export async function getGitProviders() {
  const org = await getOrCreateDefaultOrganization();

  return prisma.gitProvider.findMany({
    where: { organizationId: org.id },
    orderBy: { createdAt: "desc" },
    include: {
      _count: {
        select: { repositories: true },
      },
    },
  });
}

export async function getGitProvider(id: string) {
  return prisma.gitProvider.findUnique({
    where: { id },
    include: {
      repositories: {
        orderBy: { name: "asc" },
      },
    },
  });
}

export async function createGitProvider(
  formData: FormData,
): Promise<ActionResult<{ id: string }>> {
  const rawData = {
    type: formData.get("type"),
    name: formData.get("name"),
    baseUrl: formData.get("baseUrl"),
    accessToken: formData.get("accessToken"),
    webhookSecret: formData.get("webhookSecret"),
  };

  const parsed = createGitProviderSchema.safeParse(rawData);

  if (!parsed.success) {
    const fieldErrors: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const field = issue.path[0]?.toString();
      if (field && !fieldErrors[field]) {
        fieldErrors[field] = issue.message;
      }
    }
    return {
      success: false,
      error: parsed.error.issues[0]?.message ?? "Invalid data",
      fieldErrors,
    };
  }

  const org = await getOrCreateDefaultOrganization();

  try {
    const provider = await prisma.gitProvider.create({
      data: {
        type: parsed.data.type as GitProviderType,
        name: parsed.data.name,
        baseUrl: parsed.data.baseUrl,
        accessToken: parsed.data.accessToken,
        webhookSecret: parsed.data.webhookSecret,
        organizationId: org.id,
      },
    });

    revalidatePath("/git-providers");
    return { success: true, data: { id: provider.id } };
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("Unique constraint failed")
    ) {
      return {
        success: false,
        error: "A provider with this type and name already exists",
      };
    }
    return {
      success: false,
      error: "Failed to create git provider",
    };
  }
}

export async function updateGitProvider(
  formData: FormData,
): Promise<ActionResult> {
  const rawData = {
    id: formData.get("id"),
    type: formData.get("type"),
    name: formData.get("name"),
    baseUrl: formData.get("baseUrl"),
    accessToken: formData.get("accessToken"),
    webhookSecret: formData.get("webhookSecret"),
  };

  const parsed = updateGitProviderSchema.safeParse(rawData);

  if (!parsed.success) {
    const fieldErrors: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const field = issue.path[0]?.toString();
      if (field && !fieldErrors[field]) {
        fieldErrors[field] = issue.message;
      }
    }
    return {
      success: false,
      error: parsed.error.issues[0]?.message ?? "Invalid data",
      fieldErrors,
    };
  }

  try {
    const updateData: Record<string, unknown> = {
      type: parsed.data.type as GitProviderType,
      name: parsed.data.name,
      baseUrl: parsed.data.baseUrl,
      webhookSecret: parsed.data.webhookSecret,
    };

    // Only update access token if provided
    if (parsed.data.accessToken) {
      updateData.accessToken = parsed.data.accessToken;
    }

    await prisma.gitProvider.update({
      where: { id: parsed.data.id },
      data: updateData,
    });

    revalidatePath("/git-providers");
    revalidatePath(`/git-providers/${parsed.data.id}`);
    return { success: true, data: undefined };
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("Unique constraint failed")
    ) {
      return {
        success: false,
        error: "A provider with this type and name already exists",
      };
    }
    return {
      success: false,
      error: "Failed to update git provider",
    };
  }
}

export async function deleteGitProvider(id: string): Promise<ActionResult> {
  try {
    await prisma.gitProvider.delete({
      where: { id },
    });

    revalidatePath("/git-providers");
    return { success: true, data: undefined };
  } catch {
    return {
      success: false,
      error: "Failed to delete git provider",
    };
  }
}

export async function toggleGitProviderStatus(
  id: string,
  isActive: boolean,
): Promise<ActionResult> {
  try {
    await prisma.gitProvider.update({
      where: { id },
      data: { isActive },
    });

    revalidatePath("/git-providers");
    revalidatePath(`/git-providers/${id}`);
    return { success: true, data: undefined };
  } catch {
    return {
      success: false,
      error: "Failed to update provider status",
    };
  }
}

export async function redirectToGitProviders(lang: string) {
  redirect(`/${lang}/git-providers`);
}
