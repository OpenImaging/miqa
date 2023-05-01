import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:8081/');
  await page.goto('http://localhost:8000/accounts/login/?next=/oauth/authorize/%3Fredirect_uri%3Dhttp%253A%252F%252Flocalhost%253A8081%252F%26client_id%3DcBmD6D6F2YAmMWHNQZFPUr4OpaXVpW5w4Thod6Kj%26response_type%3Dcode%26state%3Dy5Nq6SATrH%26response_mode%3Dquery%26code_challenge%3DSwZrfGNbQD1jyielzKNvX2d3c1A8CtQuVCjsYE4BtCA%26code_challenge_method%3DS256');
  await page.getByPlaceholder('E-mail address').click();
  await page.getByPlaceholder('E-mail address').fill('user@localhost.local');
  await page.getByPlaceholder('Password').fill('password');
  await page.getByRole('button', { name: 'Sign In ' }).click();
  await page.getByText('Test').click();
  await page.getByRole('link', { name: 'coronacases_001.nii.gz' }).click();
  await page.locator('div:nth-child(2) > button:nth-child(2)').click();
  await page.getByLabel('Experiment Notes').click();
  await page.getByPlaceholder('There are no notes on this experiment.').fill('These are notes');
  await page.getByText('Save Note').click();
  await page.getByText('Lesions').click();
  await page.getByText('Partial Coverage').click();
  await page.getByLabel('Evaluation Comment').click();
  await page.getByPlaceholder('Write a comment about the scan').fill('These are problems');
  await page.getByRole('button', { name: 'Questionable' }).click();
  await page.locator('.transparent-btn').first().click();
  const mask = await page.locator('.scan-decision');
  await expect(page).toHaveScreenshot({ mask: [mask] });
});
