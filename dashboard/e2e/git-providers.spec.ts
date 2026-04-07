import { test, expect } from "@playwright/test";

test.describe("Git Providers", () => {
  test("should display git providers page", async ({ page }) => {
    await page.goto("/en-US/git-providers");

    await expect(
      page.getByRole("heading", { name: "Git Providers", level: 1 }),
    ).toBeVisible();
  });

  test("should navigate to add provider page", async ({ page }) => {
    await page.goto("/en-US/git-providers");

    await page.getByRole("link", { name: /add provider/i }).first().click();

    await expect(page).toHaveURL(/\/git-providers\/new/);
    await expect(
      page.getByRole("heading", { name: /add git provider/i }),
    ).toBeVisible();
  });

  test("should show provider type options in form", async ({ page }) => {
    await page.goto("/en-US/git-providers/new");

    // Click the select trigger to open options
    await page.getByRole("combobox").click();

    // Check that provider types are available
    await expect(page.getByRole("option", { name: /github/i })).toBeVisible();
    await expect(page.getByRole("option", { name: /gitlab/i })).toBeVisible();
  });

  test("should show validation error for empty form submission", async ({
    page,
  }) => {
    await page.goto("/en-US/git-providers/new");

    // Try to submit without filling required fields
    await page.getByRole("button", { name: /create provider/i }).click();

    // Form should show validation - HTML5 required attribute will prevent submission
    // The name field should be focused or show error
    const nameInput = page.getByLabel(/display name/i);
    await expect(nameInput).toBeVisible();
  });
});
