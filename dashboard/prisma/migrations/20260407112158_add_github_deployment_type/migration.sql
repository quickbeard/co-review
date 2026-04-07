-- CreateEnum
CREATE TYPE "GitHubDeploymentType" AS ENUM ('user', 'app');

-- AlterTable
ALTER TABLE "GitProvider" ADD COLUMN     "appId" TEXT,
ADD COLUMN     "deploymentType" "GitHubDeploymentType",
ADD COLUMN     "privateKey" TEXT,
ALTER COLUMN "accessToken" DROP NOT NULL;
