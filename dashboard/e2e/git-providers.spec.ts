import { test, expect } from "@playwright/test";

test.describe("Git Providers", () => {
  test("should display git providers page", async ({ page }) => {
    await page.goto("/en-US/git-providers");

    await expect(
      page.getByRole("heading", { name: /Git Providers/i, level: 1 }),
    ).toBeVisible();
    await expect(page.getByText(/Manage your git repository/i)).toBeVisible();
  });

  test("should navigate to new provider page", async ({ page }) => {
    await page.goto("/en-US/git-providers");

    // Use .first() since there might be multiple "Add Provider" links (in header and empty state)
    await page
      .getByRole("link", { name: /Add Provider/i })
      .first()
      .click();

    await expect(page).toHaveURL(/\/git-providers\/new/);
    await expect(
      page.getByRole("heading", { name: /Add Git Provider/i }),
    ).toBeVisible();
  });

  test("should display new provider form with provider type select", async ({
    page,
  }) => {
    await page.goto("/en-US/git-providers/new");

    // Check form fields
    await expect(page.getByText("Provider Type")).toBeVisible();
    await expect(page.getByText("Display Name")).toBeVisible();

    // Check provider type select - click the combobox to open options
    await page.getByRole("combobox").click();
    await expect(page.getByRole("option", { name: "GitHub" })).toBeVisible();
    await expect(page.getByRole("option", { name: "GitLab" })).toBeVisible();
    await expect(page.getByRole("option", { name: "Bitbucket" })).toBeVisible();
    await expect(
      page.getByRole("option", { name: "Azure DevOps" }),
    ).toBeVisible();
  });

  test("should show deployment type options for GitHub", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    // GitHub is default, check deployment type radio buttons are visible
    // Use exact matching to avoid matching help text
    await expect(page.getByText("Deployment Type")).toBeVisible();
    await expect(
      page.getByText("Personal Access Token", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("GitHub App", { exact: true })).toBeVisible();
  });

  test("should show base URL field for self-hosted providers", async ({
    page,
  }) => {
    await page.goto("/en-US/git-providers/new");

    // Initially GitHub is selected (no base URL field)
    // Select GitLab which supports self-hosted
    await page.getByRole("combobox").click();
    await page.getByRole("option", { name: "GitLab" }).click();

    // Base URL field should now be visible - use label to be specific
    await expect(page.getByLabel(/Base URL/i)).toBeVisible();
  });

  test("should toggle between GitHub deployment types", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    // Check user deployment is default (Personal Access Token selected)
    const userRadio = page.getByRole("radio").first();
    const appRadio = page.getByRole("radio").nth(1);

    await expect(userRadio).toBeChecked();
    await expect(appRadio).not.toBeChecked();

    // Click on GitHub App radio
    await appRadio.click();

    // Now app should be checked
    await expect(appRadio).toBeChecked();
    await expect(userRadio).not.toBeChecked();

    // GitHub App specific fields should appear - use labels for specificity
    await expect(page.getByLabel(/GitHub App ID/i)).toBeVisible();
    await expect(page.getByLabel(/Private Key/i)).toBeVisible();
  });

  test("should have required fields marked", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    // Check that required fields have asterisk markers
    const requiredMarkers = await page
      .locator("span.text-destructive")
      .filter({ hasText: "*" })
      .count();
    expect(requiredMarkers).toBeGreaterThan(0);
  });

  test("should have cancel button that navigates back", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    await page.getByRole("button", { name: /Cancel/i }).click();

    await expect(page).toHaveURL(/\/git-providers$/);
  });

  test("should have back link to git providers list", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    await page.getByRole("link", { name: /Back to Git Providers/i }).click();

    await expect(page).toHaveURL(/\/git-providers$/);
  });
});
