const { chromium } = require('playwright');

async function captureScreenshots() {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to BigQuery Lite...');
    await page.goto('http://localhost:3000');
    
    // Wait for the page to load
    await page.waitForSelector('.results-section', { timeout: 10000 });
    
    // Take initial screenshot
    console.log('Taking initial screenshot...');
    await page.screenshot({ 
      path: 'initial-state.png',
      fullPage: true 
    });
    
    // Try to run a query
    console.log('Attempting to run query...');
    try {
      // Try different selectors for the editor
      const editorSelectors = ['.monaco-editor textarea', '.query-editor', 'textarea', '[contenteditable="true"]'];
      let editorFound = false;
      
      for (const selector of editorSelectors) {
        try {
          await page.click(selector, { timeout: 2000 });
          await page.keyboard.type('SELECT COUNT(*) as total_rows FROM nyc_taxi;');
          editorFound = true;
          console.log(`Editor found with selector: ${selector}`);
          break;
        } catch (e) {
          console.log(`Editor not found with selector: ${selector}`);
        }
      }
      
      if (!editorFound) {
        console.log('Could not find editor, continuing anyway...');
      }
      
      // Try different selectors for the run button
      const buttonSelectors = ['button:has-text("Run Query")', '.bq-button', 'button[type="submit"]', 'button:contains("Run")'];
      let buttonFound = false;
      
      for (const selector of buttonSelectors) {
        try {
          await page.click(selector, { timeout: 2000 });
          buttonFound = true;
          console.log(`Run button found with selector: ${selector}`);
          break;
        } catch (e) {
          console.log(`Run button not found with selector: ${selector}`);
        }
      }
      
      if (buttonFound) {
        // Wait for results or timeout
        try {
          await page.waitForSelector('.bq-table, .results-table-container table, table', { timeout: 10000 });
          console.log('Results appeared!');
        } catch (e) {
          console.log('No results appeared, continuing anyway...');
        }
      }
    } catch (e) {
      console.log('Query execution failed, continuing with current state...');
    }
    
    // Take screenshot of Results tab
    console.log('Taking Results tab screenshot...');
    await page.screenshot({ 
      path: 'results-tab.png',
      fullPage: true 
    });
    
    // Click on Execution Details tab
    console.log('Switching to Execution Details tab...');
    const executionTab = page.locator('text=Execution Details');
    if (await executionTab.count() > 0) {
      await executionTab.click();
      await page.waitForTimeout(1000);
      
      // Take screenshot of Execution Details tab
      console.log('Taking Execution Details tab screenshot...');
      await page.screenshot({ 
        path: 'execution-details-tab.png',
        fullPage: true 
      });
    }
    
    // Get computed styles for debugging
    console.log('Getting computed styles...');
    const resultsInfo = await page.locator('.results-info').first();
    const tabContent = await page.locator('.tab-content').first();
    const resultsTable = await page.locator('.results-table-container').first();
    
    if (await resultsInfo.count() > 0) {
      const resultsInfoStyles = await resultsInfo.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          padding: styles.padding,
          paddingLeft: styles.paddingLeft,
          paddingRight: styles.paddingRight,
        };
      });
      console.log('Results info styles:', resultsInfoStyles);
    }
    
    if (await tabContent.count() > 0) {
      const tabContentStyles = await tabContent.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          padding: styles.padding,
          paddingLeft: styles.paddingLeft,
          paddingRight: styles.paddingRight,
        };
      });
      console.log('Tab content styles:', tabContentStyles);
    }
    
    if (await resultsTable.count() > 0) {
      const resultsTableStyles = await resultsTable.evaluate(el => {
        const styles = window.getComputedStyle(el);
        return {
          padding: styles.padding,
          paddingLeft: styles.paddingLeft,
          paddingRight: styles.paddingRight,
        };
      });
      console.log('Results table container styles:', resultsTableStyles);
    }
    
    console.log('Screenshots saved successfully!');

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
}

captureScreenshots();