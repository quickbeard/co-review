"use server";

import { prisma } from "@/lib/db";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import type {
  GitProviderType,
  GitHubDeploymentType,
} from "@/generated/prisma/client";

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

const gitHubDeploymentTypeValues = ["user", "app"] as const;

// Helper to handle FormData null values
const optionalString = z
  .string()
  .optional()
  .nullable()
  .transform((val) => val || null);

const optionalUrl = z
  .string()
  .url("Must be a valid URL")
  .optional()
  .nullable()
  .or(z.literal(""))
  .transform((val) => val || null);

// Base schema for common fields
const baseGitProviderSchema = z.object({
  type: z.enum(gitProviderTypeValues),
  name: z.string().min(1, "Name is required").max(100),
  baseUrl: optionalUrl,
  webhookSecret: optionalString,
  // GitHub-specific fields
  deploymentType: z
    .enum(gitHubDeploymentTypeValues)
    .optional()
    .nullable()
    .transform((val) => val || null),
  appId: optionalString,
  privateKey: optionalString,
  accessToken: optionalString,
});

// Custom validation for create schema
const createGitProviderSchema = baseGitProviderSchema.superRefine(
  (data, ctx) => {
    if (data.type === "github") {
      // GitHub requires deploymentType
      if (!data.deploymentType) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Deployment type is required for GitHub",
          path: ["deploymentType"],
        });
        return;
      }

      if (data.deploymentType === "user") {
        // User deployment requires accessToken
        if (!data.accessToken) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Personal access token is required",
            path: ["accessToken"],
          });
        }
      } else if (data.deploymentType === "app") {
        // App deployment requires appId and privateKey
        if (!data.appId) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "GitHub App ID is required",
            path: ["appId"],
          });
        }
        if (!data.privateKey) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Private key is required",
            path: ["privateKey"],
          });
        }
      }
    } else {
      // Non-GitHub providers require accessToken
      if (!data.accessToken) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Access token is required",
          path: ["accessToken"],
        });
      }
    }
  },
);

// Update schema - tokens are optional (keep existing if not provided)
const updateGitProviderSchema = z
  .object({
    id: z.string().min(1),
  })
  .merge(baseGitProviderSchema);

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
    deploymentType: formData.get("deploymentType"),
    appId: formData.get("appId"),
    privateKey: formData.get("privateKey"),
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
        deploymentType: parsed.data
          .deploymentType as GitHubDeploymentType | null,
        appId: parsed.data.appId,
        privateKey: parsed.data.privateKey,
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
    deploymentType: formData.get("deploymentType"),
    appId: formData.get("appId"),
    privateKey: formData.get("privateKey"),
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
      deploymentType: parsed.data.deploymentType as GitHubDeploymentType | null,
    };

    // Only update access token if provided
    if (parsed.data.accessToken) {
      updateData.accessToken = parsed.data.accessToken;
    }

    // Only update appId if provided
    if (parsed.data.appId) {
      updateData.appId = parsed.data.appId;
    }

    // Only update privateKey if provided
    if (parsed.data.privateKey) {
      updateData.privateKey = parsed.data.privateKey;
    }

    // Clear GitHub-specific fields when switching away from GitHub or changing deployment type
    if (parsed.data.type !== "github") {
      updateData.deploymentType = null;
      updateData.appId = null;
      updateData.privateKey = null;
    } else if (parsed.data.deploymentType === "user") {
      // Clear app fields when switching to user deployment
      updateData.appId = null;
      updateData.privateKey = null;
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
