const { test, expect } = require('@playwright/test');

test.describe('BigQuery-Lite Workflow Capture', () => {
  test('Capture actual workflow screenshots', async ({ page }) => {
    // Go to the application
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Step 1: Initial interface
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-1-welcome.png',
      fullPage: true 
    });

    // Step 2: Click on the query editor area and clear existing content
    const editor = page.locator('.ace_editor, .monaco-editor, textarea').first();
    await editor.click();
    await page.keyboard.press('Control+a');
    await page.keyboard.press('Delete');
    
    // Wait a moment for the interface to update
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-2-editor-ready.png',
      fullPage: true 
    });

    // Step 3: Type a simple query
    await page.keyboard.type('SELECT COUNT(*) as total_trips FROM nyc_taxi;');
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-3-simple-query.png',
      fullPage: true 
    });

    // Step 4: Run the query
    const runButton = page.locator('button:has-text("Run Query"), button:has-text("Run")').first();
    await runButton.click();
    
    // Wait for query to execute
    await page.waitForTimeout(3000);
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-4-query-results.png',
      fullPage: true 
    });

    // Step 5: Try a more complex analytical query
    await editor.click();
    await page.keyboard.press('Control+a');
    await page.keyboard.type(`SELECT 
  payment_type,
  COUNT(*) as trip_count,
  AVG(fare_amount) as avg_fare,
  SUM(total_amount) as total_revenue
FROM nyc_taxi 
WHERE fare_amount > 0 AND fare_amount < 100
GROUP BY payment_type 
ORDER BY trip_count DESC;`);
    
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-5-complex-query.png',
      fullPage: true 
    });

    // Step 6: Execute the complex query
    await runButton.click();
    await page.waitForTimeout(4000);
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-6-analytical-results.png',
      fullPage: true 
    });

    // Step 7: Click on Execution Details tab if it exists
    const executionTab = page.locator('button:has-text("Execution Details"), [role="tab"]:has-text("Execution")').first();
    try {
      await executionTab.click({ timeout: 2000 });
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: 'docs/screenshots/onboard-7-execution-details.png',
        fullPage: true 
      });
    } catch (e) {
      // If execution details tab doesn't exist, just take another screenshot
      await page.screenshot({ 
        path: 'docs/screenshots/onboard-7-execution-details.png',
        fullPage: true 
      });
    }

    // Step 8: Explore the sidebar - click on different sections
    try {
      // Try to click on Schemas tab
      const schemasTab = page.locator('button:has-text("Schemas"), [role="tab"]:has-text("Schema")').first();
      await schemasTab.click({ timeout: 2000 });
      await page.waitForTimeout(1000);
    } catch (e) {
      console.log('No schemas tab found');
    }
    
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-8-schemas-browser.png',
      fullPage: true 
    });

    // Step 9: Try changing the engine from DuckDB to ClickHouse
    try {
      const engineSelect = page.locator('select:has-option("DuckDB"), select:has-option("ClickHouse")').first();
      await engineSelect.selectOption({ label: 'ClickHouse' });
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: 'docs/screenshots/onboard-9-engine-switch.png',
        fullPage: true 
      });
    } catch (e) {
      // If engine switch doesn't work, just take current screenshot
      await page.screenshot({ 
        path: 'docs/screenshots/onboard-9-engine-switch.png',
        fullPage: true 
      });
    }

    // Step 10: Final comprehensive view
    await page.screenshot({ 
      path: 'docs/screenshots/onboard-10-complete-interface.png',
      fullPage: true 
    });
  });
});