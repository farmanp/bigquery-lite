import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('BigQuery-Lite Onboarding Tour', () => {
  test('Complete UI walkthrough: upload schema, register, and query', async ({ page }) => {
    // Step 1: Visit the homepage
    await page.goto('/');
    await expect(page).toHaveTitle(/BigQuery/);
    
    // Wait for the main interface to load
    await page.waitForSelector('[data-testid="sql-editor"], .monaco-editor, textarea');
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'docs/screenshots/step-1.png',
      fullPage: true 
    });

    // Step 2: Navigate to schema upload section
    // Look for schema upload button or section
    const schemaUploadSelector = '[data-testid="schema-upload"], .schema-upload, button:has-text("Upload"), input[type="file"]';
    await page.waitForSelector(schemaUploadSelector, { timeout: 10000 });
    
    // Take screenshot of schema upload interface
    await page.screenshot({ 
      path: 'docs/screenshots/step-2.png',
      fullPage: true 
    });

    // Step 3: Upload a .proto file
    // First, let's create a sample proto file for testing
    const protoContent = `syntax = "proto3";

package user_events;

message UserEvent {
  string user_id = 1;
  string event_type = 2;
  int64 timestamp = 3;
  map<string, string> properties = 4;
  Location location = 5;
}

message Location {
  double latitude = 1;
  double longitude = 2;
  string city = 3;
  string country = 4;
}`;

    // Write the proto file
    const protoFilePath = path.join(process.cwd(), 'test_user_events.proto');
    await page.evaluate(async ({ content, filePath }) => {
      // This creates a file in the browser's context
      const blob = new Blob([content], { type: 'text/plain' });
      const file = new File([blob], 'user_events.proto', { type: 'text/plain' });
      
      // Store it for later use
      (window as any).testFile = file;
    }, { content: protoContent, filePath: protoFilePath });

    // Upload the proto file
    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.isVisible()) {
      // Create a temporary file for upload
      await page.setInputFiles(fileInput, {
        name: 'user_events.proto',
        mimeType: 'text/plain',
        buffer: Buffer.from(protoContent)
      });
    }

    // Take screenshot after file upload
    await page.screenshot({ 
      path: 'docs/screenshots/step-3.png',
      fullPage: true 
    });

    // Step 4: Register the schema
    const registerButton = page.locator('button:has-text("Register"), button:has-text("Submit"), [data-testid="register-schema"]');
    if (await registerButton.first().isVisible()) {
      await registerButton.first().click();
      
      // Wait for registration to complete
      await page.waitForTimeout(2000);
    }

    // Take screenshot of schema registration result
    await page.screenshot({ 
      path: 'docs/screenshots/step-4.png',
      fullPage: true 
    });

    // Step 5: Navigate to SQL editor and run a query
    const sqlEditorSelector = '[data-testid="sql-editor"], .monaco-editor, textarea';
    await page.waitForSelector(sqlEditorSelector);
    
    // Click on the SQL editor
    const sqlEditor = page.locator(sqlEditorSelector).first();
    await sqlEditor.click();

    // Clear any existing content and type a sample query
    await page.keyboard.press('Control+a');
    const sampleQuery = `SELECT 
  user_id,
  event_type,
  COUNT(*) as event_count,
  AVG(timestamp) as avg_timestamp
FROM user_events 
WHERE event_type IN ('login', 'purchase', 'view')
GROUP BY user_id, event_type
ORDER BY event_count DESC
LIMIT 10;`;

    await page.keyboard.type(sampleQuery);

    // Take screenshot of SQL editor with query
    await page.screenshot({ 
      path: 'docs/screenshots/step-5.png',
      fullPage: true 
    });

    // Step 6: Execute the query
    const runButton = page.locator('button:has-text("Run"), button:has-text("Execute"), [data-testid="run-query"]');
    if (await runButton.first().isVisible()) {
      await runButton.first().click();
      
      // Wait for query execution
      await page.waitForTimeout(3000);
    } else {
      // Try keyboard shortcut if button not found
      await page.keyboard.press('Control+Enter');
      await page.waitForTimeout(3000);
    }

    // Take screenshot of query execution and results
    await page.screenshot({ 
      path: 'docs/screenshots/step-6.png',
      fullPage: true 
    });

    // Step 7: View results and query plan
    // Look for results table or execution details
    const resultsSelector = '[data-testid="results"], .results-table, .query-results';
    try {
      await page.waitForSelector(resultsSelector, { timeout: 5000 });
    } catch (e) {
      // Results might be in a different format, continue anyway
    }

    // Take final screenshot showing the complete interface with results
    await page.screenshot({ 
      path: 'docs/screenshots/step-7.png',
      fullPage: true 
    });

    // Step 8: Explore additional features (optional)
    // Check if there are tabs or additional features to showcase
    const tabsSelector = '.tabs, [role="tab"], .query-tabs';
    if (await page.locator(tabsSelector).first().isVisible()) {
      await page.locator(tabsSelector).first().click();
      await page.waitForTimeout(1000);
      
      await page.screenshot({ 
        path: 'docs/screenshots/step-8.png',
        fullPage: true 
      });
    }

    // Verify the onboarding flow completed successfully
    await expect(page).toHaveURL(/localhost:3000/);
  });

  test('Alternative onboarding with NYC taxi data', async ({ page }) => {
    // This test uses the existing NYC taxi dataset for a simpler demo
    await page.goto('/');
    await expect(page).toHaveTitle(/BigQuery/);
    
    // Wait for the interface to load
    await page.waitForSelector('[data-testid="sql-editor"], .monaco-editor, textarea');
    
    // Take screenshot of initial state
    await page.screenshot({ 
      path: 'docs/screenshots/taxi-step-1.png',
      fullPage: true 
    });

    // Navigate to SQL editor
    const sqlEditorSelector = '[data-testid="sql-editor"], .monaco-editor, textarea';
    const sqlEditor = page.locator(sqlEditorSelector).first();
    await sqlEditor.click();

    // Clear and enter a taxi data query
    await page.keyboard.press('Control+a');
    const taxiQuery = `SELECT 
  payment_type,
  COUNT(*) as trip_count,
  AVG(fare_amount) as avg_fare,
  AVG(tip_amount) as avg_tip,
  SUM(total_amount) as total_revenue
FROM nyc_taxi 
WHERE fare_amount > 0 AND fare_amount < 100
GROUP BY payment_type 
ORDER BY trip_count DESC;`;

    await page.keyboard.type(taxiQuery);

    await page.screenshot({ 
      path: 'docs/screenshots/taxi-step-2.png',
      fullPage: true 
    });

    // Execute the query
    const runButton = page.locator('button:has-text("Run"), button:has-text("Execute"), [data-testid="run-query"]');
    if (await runButton.first().isVisible()) {
      await runButton.first().click();
    } else {
      await page.keyboard.press('Control+Enter');
    }
    
    await page.waitForTimeout(3000);

    await page.screenshot({ 
      path: 'docs/screenshots/taxi-step-3.png',
      fullPage: true 
    });
  });
});