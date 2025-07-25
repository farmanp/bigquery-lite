const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function captureScreenshots() {
  // Create screenshots directory
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 1000 }
  });
  const page = await context.newPage();

  try {
    console.log('🔄 Navigating to BigQuery-Lite...');
    
    // Navigate to the application
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });

    // Wait for the app to load
    await page.waitForSelector('.app', { timeout: 10000 });
    
    console.log('📸 Capturing main interface...');
    
    // 1. Capture main interface
    await page.screenshot({ 
      path: path.join(screenshotsDir, '01-main-interface.png'),
      fullPage: false
    });

    // 2. Capture SQL editor with sample query
    console.log('📸 Capturing SQL editor...');
    
    // Clear the editor and add a sample query
    const editor = await page.locator('.monaco-editor');
    await editor.click();
    await page.keyboard.down('Control');
    await page.keyboard.press('a');
    await page.keyboard.up('Control');
    
    const sampleQuery = `-- BigQuery-Lite Analytics Demo
SELECT 
    payment_type,
    COUNT(*) as trip_count,
    AVG(fare_amount) as avg_fare,
    SUM(total_amount) as total_revenue
FROM nyc_taxi 
WHERE fare_amount > 0 
GROUP BY payment_type 
ORDER BY trip_count DESC;`;
    
    await page.keyboard.type(sampleQuery);
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: path.join(screenshotsDir, '02-sql-editor.png'),
      fullPage: false
    });

    // 3. Execute query with DuckDB
    console.log('📸 Executing DuckDB query...');
    
    // Make sure DuckDB is selected
    const engineSelector = page.locator('select').first();
    await engineSelector.selectOption('duckdb');
    
    // Execute the query
    const runButton = page.locator('button:has-text("Run Query")');
    await runButton.click();
    
    // Wait for results
    await page.waitForSelector('.results-table-container', { timeout: 15000 });
    await page.waitForTimeout(2000);
    
    await page.screenshot({ 
      path: path.join(screenshotsDir, '03-duckdb-results.png'),
      fullPage: false
    });

    // 4. Switch to ClickHouse and run the same query
    console.log('📸 Executing ClickHouse query...');
    
    await engineSelector.selectOption('clickhouse');
    await page.waitForTimeout(500);
    
    await runButton.click();
    
    // Wait for ClickHouse results
    await page.waitForTimeout(5000);
    
    await page.screenshot({ 
      path: path.join(screenshotsDir, '04-clickhouse-results.png'),
      fullPage: false
    });

    // 5. Capture query plan view
    console.log('📸 Capturing query plan...');
    
    // Switch to query plan tab if available
    const queryPlanTab = page.locator('button:has-text("Query Plan")');
    if (await queryPlanTab.count() > 0) {
      await queryPlanTab.click();
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: path.join(screenshotsDir, '05-query-plan.png'),
        fullPage: false
      });
    }

    // 6. Capture job history
    console.log('📸 Capturing job history...');
    
    const historyTab = page.locator('button:has-text("Job History")');
    if (await historyTab.count() > 0) {
      await historyTab.click();
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: path.join(screenshotsDir, '06-job-history.png'),
        fullPage: false
      });
    }

    // 7. Try a simpler query to show the interface clearly
    console.log('📸 Capturing simple query example...');
    
    // Go back to SQL editor
    const sqlTab = page.locator('button:has-text("SQL Editor")');
    if (await sqlTab.count() > 0) {
      await sqlTab.click();
    }
    
    // Clear and enter a simple query
    await editor.click();
    await page.keyboard.down('Control');
    await page.keyboard.press('a');
    await page.keyboard.up('Control');
    
    const simpleQuery = `SELECT COUNT(*) as total_trips FROM nyc_taxi;`;
    await page.keyboard.type(simpleQuery);
    await page.waitForTimeout(500);
    
    await runButton.click();
    await page.waitForTimeout(3000);
    
    await page.screenshot({ 
      path: path.join(screenshotsDir, '07-simple-query.png'),
      fullPage: false
    });

    console.log('✅ All screenshots captured successfully!');

  } catch (error) {
    console.error('❌ Error capturing screenshots:', error);
    
    // Capture error state
    await page.screenshot({ 
      path: path.join(screenshotsDir, 'error-state.png'),
      fullPage: true
    });
  } finally {
    await browser.close();
  }
}

// Run the screenshot capture
captureScreenshots().catch(console.error);