const { test, expect } = require('@playwright/test');

test.describe('BigQuery-Lite Onboarding Tour', () => {
  test('Complete UI walkthrough', async ({ page }) => {
    // Step 1: Visit the homepage
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'docs/screenshots/step-1.png',
      fullPage: true 
    });

    // Step 2: Look for SQL editor area
    await page.waitForTimeout(3000); // Give UI time to load
    
    // Take screenshot showing the main interface
    await page.screenshot({ 
      path: 'docs/screenshots/step-2.png',
      fullPage: true 
    });

    // Step 3: Try to interact with SQL editor
    // Look for textarea, Monaco editor, or code editor
    const editorSelectors = [
      'textarea',
      '.monaco-editor',
      '[data-testid="sql-editor"]',
      '.CodeMirror',
      'div[contenteditable="true"]'
    ];
    
    let editorFound = false;
    for (const selector of editorSelectors) {
      try {
        await page.waitForSelector(selector, { timeout: 2000 });
        await page.click(selector);
        editorFound = true;
        break;
      } catch (e) {
        continue;
      }
    }

    // Type a simple query
    if (editorFound) {
      await page.keyboard.type('SELECT COUNT(*) FROM nyc_taxi;');
    }

    await page.screenshot({ 
      path: 'docs/screenshots/step-3.png',
      fullPage: true 
    });

    // Step 4: Look for run button
    const runSelectors = [
      'button:has-text("Run")',
      'button:has-text("Execute")',
      '[data-testid="run-query"]',
      'button[type="submit"]',
      '.run-button'
    ];
    
    for (const selector of runSelectors) {
      try {
        await page.click(selector, { timeout: 2000 });
        break;
      } catch (e) {
        continue;
      }
    }

    // Wait for potential results
    await page.waitForTimeout(3000);

    await page.screenshot({ 
      path: 'docs/screenshots/step-4.png',
      fullPage: true 
    });

    // Step 5: Try a more complex query
    // Clear editor and type new query
    await page.keyboard.press('Control+a');
    await page.keyboard.type(`SELECT 
  payment_type,
  COUNT(*) as trip_count,
  AVG(fare_amount) as avg_fare
FROM nyc_taxi 
WHERE fare_amount > 0 
GROUP BY payment_type 
ORDER BY trip_count DESC;`);

    await page.screenshot({ 
      path: 'docs/screenshots/step-5.png',
      fullPage: true 
    });

    // Execute again
    for (const selector of runSelectors) {
      try {
        await page.click(selector, { timeout: 2000 });
        break;
      } catch (e) {
        continue;
      }
    }

    await page.waitForTimeout(5000);

    await page.screenshot({ 
      path: 'docs/screenshots/step-6.png',
      fullPage: true 
    });

    // Step 6: Look for schema browser or additional features
    const sidebarSelectors = [
      '.sidebar',
      '.schema-browser',
      '[data-testid="sidebar"]',
      '.left-panel'
    ];
    
    for (const selector of sidebarSelectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          await element.click();
          await page.waitForTimeout(1000);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    await page.screenshot({ 
      path: 'docs/screenshots/step-7.png',
      fullPage: true 
    });

    // Step 7: Look for tabs or different views
    const tabSelectors = [
      '.tab',
      '[role="tab"]',
      '.query-tabs button',
      '.nav-tab'
    ];
    
    for (const selector of tabSelectors) {
      try {
        const tabs = await page.$$(selector);
        if (tabs.length > 1) {
          await tabs[1].click();
          await page.waitForTimeout(1000);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    await page.screenshot({ 
      path: 'docs/screenshots/step-8.png',
      fullPage: true 
    });
  });
});