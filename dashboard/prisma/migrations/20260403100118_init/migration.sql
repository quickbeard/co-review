-- CreateEnum
CREATE TYPE "GitProviderType" AS ENUM ('github', 'gitlab', 'bitbucket', 'azure_devops', 'gitea', 'gerrit');

-- CreateEnum
CREATE TYPE "LLMServerType" AS ENUM ('litellm', 'openrouter', 'ollama', 'openai', 'anthropic');

-- CreateEnum
CREATE TYPE "ReviewStatus" AS ENUM ('pending', 'in_progress', 'completed', 'failed');

-- CreateTable
CREATE TABLE "Organization" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Organization_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "GitProvider" (
    "id" TEXT NOT NULL,
    "type" "GitProviderType" NOT NULL,
    "name" TEXT NOT NULL,
    "baseUrl" TEXT,
    "accessToken" TEXT NOT NULL,
    "webhookSecret" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "organizationId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "GitProvider_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Repository" (
    "id" TEXT NOT NULL,
    "externalId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "fullName" TEXT NOT NULL,
    "defaultBranch" TEXT NOT NULL DEFAULT 'main',
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "settings" JSONB,
    "gitProviderId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Repository_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "LLMServer" (
    "id" TEXT NOT NULL,
    "type" "LLMServerType" NOT NULL,
    "name" TEXT NOT NULL,
    "baseUrl" TEXT NOT NULL,
    "apiKey" TEXT,
    "defaultModel" TEXT NOT NULL,
    "fallbackModels" TEXT[],
    "maxTokens" INTEGER NOT NULL DEFAULT 32000,
    "timeout" INTEGER NOT NULL DEFAULT 120,
    "isDefault" BOOLEAN NOT NULL DEFAULT false,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "organizationId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "LLMServer_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ReviewContext" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "content" TEXT NOT NULL,
    "isGlobal" BOOLEAN NOT NULL DEFAULT false,
    "priority" INTEGER NOT NULL DEFAULT 0,
    "organizationId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ReviewContext_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Review" (
    "id" TEXT NOT NULL,
    "prNumber" INTEGER NOT NULL,
    "prTitle" TEXT NOT NULL,
    "prUrl" TEXT NOT NULL,
    "prAuthor" TEXT,
    "baseBranch" TEXT,
    "headBranch" TEXT,
    "status" "ReviewStatus" NOT NULL DEFAULT 'pending',
    "score" INTEGER,
    "summary" TEXT,
    "findings" JSONB,
    "suggestions" JSONB,
    "metadata" JSONB,
    "tokensUsed" INTEGER,
    "promptTokens" INTEGER,
    "completionTokens" INTEGER,
    "durationMs" INTEGER,
    "errorMessage" TEXT,
    "repositoryId" TEXT NOT NULL,
    "organizationId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "completedAt" TIMESTAMP(3),

    CONSTRAINT "Review_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Organization_slug_key" ON "Organization"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "GitProvider_organizationId_type_name_key" ON "GitProvider"("organizationId", "type", "name");

-- CreateIndex
CREATE UNIQUE INDEX "Repository_gitProviderId_externalId_key" ON "Repository"("gitProviderId", "externalId");

-- CreateIndex
CREATE UNIQUE INDEX "LLMServer_organizationId_name_key" ON "LLMServer"("organizationId", "name");

-- CreateIndex
CREATE UNIQUE INDEX "ReviewContext_organizationId_name_key" ON "ReviewContext"("organizationId", "name");

-- CreateIndex
CREATE INDEX "Review_organizationId_createdAt_idx" ON "Review"("organizationId", "createdAt");

-- CreateIndex
CREATE INDEX "Review_repositoryId_createdAt_idx" ON "Review"("repositoryId", "createdAt");

-- CreateIndex
CREATE INDEX "Review_status_idx" ON "Review"("status");

-- AddForeignKey
ALTER TABLE "GitProvider" ADD CONSTRAINT "GitProvider_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Repository" ADD CONSTRAINT "Repository_gitProviderId_fkey" FOREIGN KEY ("gitProviderId") REFERENCES "GitProvider"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LLMServer" ADD CONSTRAINT "LLMServer_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ReviewContext" ADD CONSTRAINT "ReviewContext_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Review" ADD CONSTRAINT "Review_repositoryId_fkey" FOREIGN KEY ("repositoryId") REFERENCES "Repository"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Review" ADD CONSTRAINT "Review_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE CASCADE ON UPDATE CASCADE;
