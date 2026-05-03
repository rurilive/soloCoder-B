const { test, expect } = require('@playwright/test');

test.describe.configure({ mode: 'serial' });

test.describe('Event Management', () => {
  const testPassword = 'Test1234';

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  async function registerUser(page, username) {
    const email = `${username}@test.com`;
    
    await page.getByRole('button', { name: '注册' }).click();
    await page.waitForSelector('form', { timeout: 5000 });
    
    const formGroups = page.locator('.form-group');
    await formGroups.nth(0).locator('input').fill(username);
    await formGroups.nth(1).locator('input').fill(email);
    await formGroups.nth(2).locator('input').fill(testPassword);
    
    const submitButton = page.locator('form').getByRole('button', { name: '注册' });
    await submitButton.click();
    
    await expect(page.getByText('注册并登录成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByText(`当前用户: ${username}`)).toBeVisible({ timeout: 30000 });
  }

  function getFutureDateString(days = 1) {
    const futureDate = new Date(Date.now() + days * 86400000);
    return futureDate.toISOString().slice(0, 10);
  }

  test('should show events tab after login', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_event_tab_${timestamp}`;
    
    await registerUser(page, testUsername);
    
    await expect(page.getByRole('button', { name: '我的日程' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: '公开日程' })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('button', { name: '我的会议' })).toBeVisible({ timeout: 30000 });
  });

  test('should show empty state when no events', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_event_empty_${timestamp}`;
    
    await registerUser(page, testUsername);
    
    await expect(page.getByText('暂无日程，点击上方按钮创建第一个日程')).toBeVisible({ timeout: 30000 });
  });

  test('should create a new event successfully', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_event_create_${timestamp}`;
    const dateStr = getFutureDateString();
    
    await registerUser(page, testUsername);
    
    await page.getByRole('button', { name: '+ 创建新日程' }).click();
    await page.waitForSelector('.modal-overlay form', { timeout: 5000 });
    
    const modalFormGroups = page.locator('.modal .form-group');
    await modalFormGroups.nth(0).locator('input').fill('测试日程');
    await modalFormGroups.nth(1).locator('textarea').fill('这是一个测试日程');
    await modalFormGroups.nth(2).locator('input').fill(`${dateStr}T10:00`);
    await modalFormGroups.nth(3).locator('input').fill(`${dateStr}T11:00`);
    
    const submitButton = page.locator('.modal').getByRole('button', { name: '创建' });
    await submitButton.click();
    
    await expect(page.getByText('日程创建成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('heading', { name: '测试日程' })).toBeVisible({ timeout: 30000 });
  });

  test('should update an existing event', async ({ page }) => {
    const timestamp = Date.now();
    const testUsername = `e2e_event_update_${timestamp}`;
    const dateStr = getFutureDateString();
    
    await registerUser(page, testUsername);
    
    await page.getByRole('button', { name: '+ 创建新日程' }).click();
    await page.waitForSelector('.modal-overlay form', { timeout: 5000 });
    
    let modalFormGroups = page.locator('.modal .form-group');
    await modalFormGroups.nth(0).locator('input').fill('待更新日程');
    await modalFormGroups.nth(2).locator('input').fill(`${dateStr}T10:00`);
    await modalFormGroups.nth(3).locator('input').fill(`${dateStr}T11:00`);
    
    let submitButton = page.locator('.modal').getByRole('button', { name: '创建' });
    await submitButton.click();
    
    await expect(page.getByText('日程创建成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('heading', { name: '待更新日程' })).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '编辑' }).click();
    await page.waitForSelector('.modal-overlay form', { timeout: 5000 });
    
    modalFormGroups = page.locator('.modal .form-group');
    await modalFormGroups.nth(0).locator('input').fill('已更新的日程');
    
    submitButton = page.locator('.modal').getByRole('button', { name: '更新' });
    await submitButton.click();
    
    await expect(page.getByText('日程更新成功！')).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole('heading', { name: '已更新的日程' })).toBeVisible({ timeout: 30000 });
  });

  test('should create a public event and view in public tab', async ({ page }) => {
    const timestamp = Date.now();
    const user1 = `e2e_pub1_${timestamp}`;
    const user2 = `e2e_pub2_${timestamp}`;
    const dateStr = getFutureDateString();
    
    await registerUser(page, user1);
    
    await page.getByRole('button', { name: '+ 创建新日程' }).click();
    await page.waitForSelector('.modal-overlay form', { timeout: 5000 });
    
    const modalFormGroups = page.locator('.modal .form-group');
    await modalFormGroups.nth(0).locator('input').fill('公开测试日程');
    await modalFormGroups.nth(2).locator('input').fill(`${dateStr}T10:00`);
    await modalFormGroups.nth(3).locator('input').fill(`${dateStr}T11:00`);
    
    const checkbox = page.locator('.modal').getByText('设为公开日程');
    await checkbox.click();
    
    const submitButton = page.locator('.modal').getByRole('button', { name: '创建' });
    await submitButton.click();
    
    await expect(page.getByText('日程创建成功！')).toBeVisible({ timeout: 30000 });
    
    await page.getByRole('button', { name: '登出' }).click();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible({ timeout: 30000 });
    
    await registerUser(page, user2);
    
    await page.getByRole('button', { name: '公开日程' }).click();
    await expect(page.getByRole('heading', { name: '公开测试日程' })).toBeVisible({ timeout: 30000 });
  });
});
