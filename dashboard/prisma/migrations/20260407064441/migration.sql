/*
  Warnings:

  - You are about to drop the `LLMServer` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Review` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `ReviewContext` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "LLMServer" DROP CONSTRAINT "LLMServer_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "Review" DROP CONSTRAINT "Review_organizationId_fkey";

-- DropForeignKey
ALTER TABLE "Review" DROP CONSTRAINT "Review_repositoryId_fkey";

-- DropForeignKey
ALTER TABLE "ReviewContext" DROP CONSTRAINT "ReviewContext_organizationId_fkey";

-- DropTable
DROP TABLE "LLMServer";

-- DropTable
DROP TABLE "Review";

-- DropTable
DROP TABLE "ReviewContext";

-- DropEnum
DROP TYPE "LLMServerType";

-- DropEnum
DROP TYPE "ReviewStatus";
