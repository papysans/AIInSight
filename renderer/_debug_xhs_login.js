const { chromium } = require('playwright');

(async () => {
  const b = await chromium.launch({ headless: true });
  const ctx = await b.newContext({
    viewport: { width: 1280, height: 900 },
    locale: 'zh-CN',
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  const page = await ctx.newPage();

  console.log('[1] Navigating to xiaohongshu.com...');
  await page.goto('https://www.xiaohongshu.com', { waitUntil: 'networkidle', timeout: 30000 });
  console.log('[2] Current URL:', page.url());

  // Dump login-related elements
  const loginEls = await page.evaluate(() => {
    const els = document.querySelectorAll('[class*="login"], [class*="qr"], [class*="Login"], [class*="QR"], [id*="login"]');
    return Array.from(els).map(el => ({
      tag: el.tagName, cls: el.className.toString().slice(0, 80), id: el.id, text: (el.textContent || '').trim().slice(0, 60)
    }));
  });
  console.log('[3] Login-related elements:', JSON.stringify(loginEls, null, 2));

  // Find login buttons
  const btns = await page.evaluate(() => {
    const all = document.querySelectorAll('button, a, [role="button"], span');
    return Array.from(all)
      .filter(el => /登录|login|sign.?in/i.test(el.textContent || ''))
      .map(el => ({
        tag: el.tagName, cls: el.className.toString().slice(0, 80),
        text: (el.textContent || '').trim().slice(0, 60), href: el.href || ''
      }));
  });
  console.log('[4] Login buttons:', JSON.stringify(btns, null, 2));

  // Try clicking the login button
  const loginBtn = await page.$('text=登录');
  if (loginBtn) {
    console.log('[5] Clicking 登录 button...');
    await loginBtn.click();
    await page.waitForTimeout(3000);
    console.log('[6] URL after click:', page.url());

    // Now look for QR code
    const qrEls = await page.evaluate(() => {
      const imgs = document.querySelectorAll('img');
      return Array.from(imgs).map(img => ({
        src: img.src.slice(0, 120), cls: img.className, w: img.width, h: img.height,
        natural: img.naturalWidth + 'x' + img.naturalHeight
      }));
    });
    console.log('[7] All images after login click:', JSON.stringify(qrEls, null, 2));

    // Also check for canvas or iframe
    const canvases = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('canvas, iframe')).map(el => ({
        tag: el.tagName, cls: el.className, id: el.id, src: el.src || '',
        w: el.width, h: el.height
      }));
    });
    console.log('[8] Canvas/iframe elements:', JSON.stringify(canvases, null, 2));

    // Check for QR-specific containers
    const qrContainers = await page.evaluate(() => {
      const els = document.querySelectorAll('[class*="qr"], [class*="QR"], [class*="qrcode"], [class*="code-container"]');
      return Array.from(els).map(el => ({
        tag: el.tagName, cls: el.className.toString().slice(0, 100),
        html: el.innerHTML.slice(0, 200)
      }));
    });
    console.log('[9] QR containers:', JSON.stringify(qrContainers, null, 2));
  } else {
    console.log('[5] No 登录 button found');
    // Take full page screenshot for debugging
  }

  // Also try direct login URL
  console.log('[10] Trying direct QR login URL...');
  await page.goto('https://www.xiaohongshu.com/login', { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
  console.log('[11] URL:', page.url());

  const allImgs2 = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('img')).map(img => ({
      src: img.src.slice(0, 120), w: img.width, h: img.height
    }));
  });
  console.log('[12] Images on /login page:', JSON.stringify(allImgs2, null, 2));

  await b.close();
  console.log('[DONE]');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
