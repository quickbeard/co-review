import { describe, it, expect, vi, beforeEach } from "vitest";
import { prisma } from "@/lib/db";
import {
  getGitProviders,
  getGitProvider,
  createGitProvider,
  updateGitProvider,
  deleteGitProvider,
  toggleGitProviderStatus,
} from "@/lib/actions/git-providers";

// Mock prisma
vi.mock("@/lib/db", () => ({
  prisma: {
    organization: {
      findUnique: vi.fn(),
      create: vi.fn(),
    },
    gitProvider: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

// Mock next/cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

const mockOrganization = {
  id: "org-1",
  name: "Default Organization",
  slug: "default",
  createdAt: new Date(),
  updatedAt: new Date(),
};

const mockGitProvider = {
  id: "provider-1",
  type: "github" as const,
  name: "My GitHub",
  baseUrl: null,
  accessToken: "ghp_xxx",
  webhookSecret: null,
  isActive: true,
  organizationId: "org-1",
  deploymentType: "user" as const,
  appId: null,
  privateKey: null,
  createdAt: new Date(),
  updatedAt: new Date(),
};

function createFormData(data: Record<string, string>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(data)) {
    formData.append(key, value);
  }
  return formData;
}

describe("Git Provider Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(prisma.organization.findUnique).mockResolvedValue(
      mockOrganization,
    );
  });

  describe("getGitProviders", () => {
    it("should return all git providers for the organization", async () => {
      const mockProviders = [
        { ...mockGitProvider, _count: { repositories: 2 } },
      ];
      vi.mocked(prisma.gitProvider.findMany).mockResolvedValue(
        mockProviders as never,
      );

      const result = await getGitProviders();

      expect(result).toEqual(mockProviders);
      expect(prisma.gitProvider.findMany).toHaveBeenCalledWith({
        where: { organizationId: mockOrganization.id },
        orderBy: { createdAt: "desc" },
        include: {
          _count: {
            select: { repositories: true },
          },
        },
      });
    });

    it("should create default organization if it does not exist", async () => {
      vi.mocked(prisma.organization.findUnique).mockResolvedValue(null);
      vi.mocked(prisma.organization.create).mockResolvedValue(mockOrganization);
      vi.mocked(prisma.gitProvider.findMany).mockResolvedValue([]);

      await getGitProviders();

      expect(prisma.organization.create).toHaveBeenCalledWith({
        data: {
          name: "Default Organization",
          slug: "default",
        },
      });
    });
  });

  describe("getGitProvider", () => {
    it("should return a git provider by id with repositories", async () => {
      const mockProviderWithRepos = {
        ...mockGitProvider,
        repositories: [],
      };
      vi.mocked(prisma.gitProvider.findUnique).mockResolvedValue(
        mockProviderWithRepos as never,
      );

      const result = await getGitProvider("provider-1");

      expect(result).toEqual(mockProviderWithRepos);
      expect(prisma.gitProvider.findUnique).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        include: {
          repositories: {
            orderBy: { name: "asc" },
          },
        },
      });
    });

    it("should return null if provider not found", async () => {
      vi.mocked(prisma.gitProvider.findUnique).mockResolvedValue(null);

      const result = await getGitProvider("non-existent");

      expect(result).toBeNull();
    });
  });

  describe("createGitProvider", () => {
    it("should create a GitHub provider with user deployment type", async () => {
      vi.mocked(prisma.gitProvider.create).mockResolvedValue(
        mockGitProvider as never,
      );

      const formData = createFormData({
        type: "github",
        name: "My GitHub",
        baseUrl: "",
        accessToken: "ghp_xxx",
        webhookSecret: "",
        deploymentType: "user",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.id).toBe("provider-1");
      }
      expect(prisma.gitProvider.create).toHaveBeenCalledWith({
        data: {
          type: "github",
          name: "My GitHub",
          baseUrl: null,
          accessToken: "ghp_xxx",
          webhookSecret: null,
          deploymentType: "user",
          appId: null,
          privateKey: null,
          organizationId: mockOrganization.id,
        },
      });
    });

    it("should create a GitHub provider with app deployment type", async () => {
      vi.mocked(prisma.gitProvider.create).mockResolvedValue({
        ...mockGitProvider,
        deploymentType: "app",
        accessToken: null,
        appId: "123456",
        privateKey:
          "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
      } as never);

      const formData = createFormData({
        type: "github",
        name: "My GitHub App",
        baseUrl: "",
        deploymentType: "app",
        appId: "123456",
        privateKey:
          "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        webhookSecret: "secret123",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(true);
    });

    it("should create a non-GitHub provider with access token", async () => {
      vi.mocked(prisma.gitProvider.create).mockResolvedValue({
        ...mockGitProvider,
        type: "gitlab",
        accessToken: "glpat_xxx",
        deploymentType: null,
      } as never);

      const formData = createFormData({
        type: "gitlab",
        name: "My GitLab",
        baseUrl: "",
        accessToken: "glpat_xxx",
        webhookSecret: "",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(true);
    });

    it("should return error for missing name", async () => {
      const formData = createFormData({
        type: "github",
        name: "",
        accessToken: "ghp_xxx",
        deploymentType: "user",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toContain("Name is required");
      }
    });

    it("should return error for missing access token on GitHub user deployment", async () => {
      const formData = createFormData({
        type: "github",
        name: "My GitHub",
        accessToken: "",
        deploymentType: "user",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.fieldErrors?.accessToken).toBeDefined();
      }
    });

    it("should return error for missing app fields on GitHub app deployment", async () => {
      const formData = createFormData({
        type: "github",
        name: "My GitHub App",
        deploymentType: "app",
        appId: "",
        privateKey: "",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(
          result.fieldErrors?.appId || result.fieldErrors?.privateKey,
        ).toBeDefined();
      }
    });

    it("should return error for missing access token on non-GitHub provider", async () => {
      const formData = createFormData({
        type: "gitlab",
        name: "My GitLab",
        accessToken: "",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.fieldErrors?.accessToken).toBeDefined();
      }
    });

    it("should return error for invalid base URL", async () => {
      const formData = createFormData({
        type: "gitlab",
        name: "My GitLab",
        baseUrl: "not-a-url",
        accessToken: "glpat_xxx",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toContain("valid URL");
      }
    });

    it("should handle unique constraint violation", async () => {
      vi.mocked(prisma.gitProvider.create).mockRejectedValue(
        new Error("Unique constraint failed"),
      );

      const formData = createFormData({
        type: "github",
        name: "My GitHub",
        baseUrl: "",
        accessToken: "ghp_xxx",
        webhookSecret: "",
        deploymentType: "user",
      });

      const result = await createGitProvider(formData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toContain("already exists");
      }
    });
  });

  describe("updateGitProvider", () => {
    it("should update a git provider with valid data", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue(
        mockGitProvider as never,
      );

      const formData = createFormData({
        id: "provider-1",
        type: "github",
        name: "Updated GitHub",
        baseUrl: "",
        accessToken: "",
        webhookSecret: "",
        deploymentType: "user",
      });

      const result = await updateGitProvider(formData);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: {
          type: "github",
          name: "Updated GitHub",
          baseUrl: null,
          webhookSecret: null,
          deploymentType: "user",
          appId: null,
          privateKey: null,
        },
      });
    });

    it("should update access token only if provided", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue(
        mockGitProvider as never,
      );

      const formData = createFormData({
        id: "provider-1",
        type: "github",
        name: "My GitHub",
        baseUrl: "",
        accessToken: "new_token",
        webhookSecret: "",
        deploymentType: "user",
      });

      const result = await updateGitProvider(formData);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: expect.objectContaining({
          accessToken: "new_token",
        }),
      });
    });

    it("should clear app fields when switching to user deployment", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue(
        mockGitProvider as never,
      );

      const formData = createFormData({
        id: "provider-1",
        type: "github",
        name: "My GitHub",
        baseUrl: "",
        accessToken: "ghp_xxx",
        webhookSecret: "",
        deploymentType: "user",
      });

      const result = await updateGitProvider(formData);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: expect.objectContaining({
          deploymentType: "user",
          appId: null,
          privateKey: null,
        }),
      });
    });

    it("should clear GitHub fields when switching to non-GitHub provider", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue({
        ...mockGitProvider,
        type: "gitlab",
        deploymentType: null,
      } as never);

      const formData = createFormData({
        id: "provider-1",
        type: "gitlab",
        name: "My GitLab",
        baseUrl: "",
        accessToken: "glpat_xxx",
        webhookSecret: "",
      });

      const result = await updateGitProvider(formData);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: expect.objectContaining({
          deploymentType: null,
          appId: null,
          privateKey: null,
        }),
      });
    });

    it("should return error for missing id", async () => {
      const formData = createFormData({
        type: "github",
        name: "My GitHub",
        deploymentType: "user",
      });

      const result = await updateGitProvider(formData);

      expect(result.success).toBe(false);
    });
  });

  describe("deleteGitProvider", () => {
    it("should delete a git provider", async () => {
      vi.mocked(prisma.gitProvider.delete).mockResolvedValue(
        mockGitProvider as never,
      );

      const result = await deleteGitProvider("provider-1");

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.delete).toHaveBeenCalledWith({
        where: { id: "provider-1" },
      });
    });

    it("should return error if delete fails", async () => {
      vi.mocked(prisma.gitProvider.delete).mockRejectedValue(
        new Error("Not found"),
      );

      const result = await deleteGitProvider("non-existent");

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Failed to delete git provider");
      }
    });
  });

  describe("toggleGitProviderStatus", () => {
    it("should toggle provider to active", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue({
        ...mockGitProvider,
        isActive: true,
      } as never);

      const result = await toggleGitProviderStatus("provider-1", true);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: { isActive: true },
      });
    });

    it("should toggle provider to inactive", async () => {
      vi.mocked(prisma.gitProvider.update).mockResolvedValue({
        ...mockGitProvider,
        isActive: false,
      } as never);

      const result = await toggleGitProviderStatus("provider-1", false);

      expect(result.success).toBe(true);
      expect(prisma.gitProvider.update).toHaveBeenCalledWith({
        where: { id: "provider-1" },
        data: { isActive: false },
      });
    });

    it("should return error if toggle fails", async () => {
      vi.mocked(prisma.gitProvider.update).mockRejectedValue(
        new Error("Not found"),
      );

      const result = await toggleGitProviderStatus("non-existent", true);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Failed to update provider status");
      }
    });
  });
});
