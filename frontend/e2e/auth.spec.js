const { test, expect } = require('@playwright/test');

test.describe.configure({ mode: 'serial' });

test.describe('User Authentication', () => {
  const testPassword = 'Test1234';

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should show login and register buttons when not authenticated', async ({ page }) => {
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
    await expect(page.getByRole('button', { name: '注册' })).toBeVisible();
  });

  test('should register a new user successfully', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_reg_${timestamp}`;
    const testEmail = `e2e_reg${timestamp}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    const formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testEmail);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    const submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText('注册并登录成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(`当前用户: ${testUsername}`)).toBeVisible({ timeout: 30000 });
  });

  test('should logout successfully', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_logout_${timestamp}`;
    const testEmail = `e2e_logout${timestamp}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    const formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testEmail);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    const submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText(`当前用户: ${testUsername}`)).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登出' }).click();
    
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: '注册' })).toBeVisible({ timeout: 30000 });
  });

  test('should show error for duplicate username', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_dup_${timestamp}`;
    const testEmail = `e2e_dup${timestamp}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    let formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testEmail);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    let submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText('注册并登录成功！')).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登出' }).click();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(`another${testEmail}`);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText('用户名已存在')).toBeVisible({ timeout: 30000 });
  });

  test('should show error for weak password', async ({ page }) => {
    const timestamp = Date.now();
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    const formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(`e2e_weak_${timestamp}`);
    await formGroups.nth(2).locator('input').fill('weakpass');
    
    await expect(page.getByText('密码强度不足')).toBeVisible({ timeout: 10000 });
    
    const submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText('密码必须包含至少两类字符')).toBeVisible({ timeout: 10000 });
  });

  test('should login with valid credentials', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_login_${timestamp}`;
    const testEmail = `e2e_login${timestamp}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    let formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testEmail);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    let submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText(`当前用户: ${testUsername}`)).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登出' }).click();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testPassword);
    
    submitButton = page.locator('form').getByRole('button', { name: '登录' });
    await submitButton.click();
    
    await expect(page.getByText('登录成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(`当前用户: ${testUsername}`)).toBeVisible({ timeout: 30000 });
  });

  test('should show error for wrong password', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_wrong_${timestamp}`;
    const testEmail = `e2e_wrong${timestamp}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    let formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill(testEmail);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    let submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText(`当前用户: ${testUsername}`)).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登出' }).click();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(testUsername);
    await formGroups.nth(1).locator('input').fill('WrongPass123');
    
    submitButton = page.locator('form').getByRole('button', { name: '登录' });
    await submitButton.click();
    
    await expect(page.getByText('用户名或密码错误')).toBeVisible({ timeout: 30000 });
  });
});
