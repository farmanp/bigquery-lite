const { chromium } = require('playwright');

async function captureScreenshot() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Set viewport size for consistent screenshots
  await page.setViewportSize({ width: 1400, height: 900 });
  
  try {
    // Navigate to the application
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    
    // Wait a bit for any animations or loading to complete
    await page.waitForTimeout(2000);
    
    // Take a screenshot
    await page.screenshot({ 
      path: 'bigquery-lite-ui-updated.png',
      fullPage: false
    });
    
    console.log('Screenshot captured: bigquery-lite-ui-updated.png');
    
  } catch (error) {
    console.error('Error capturing screenshot:', error);
  } finally {
    await browser.close();
  }
}

captureScreenshot();