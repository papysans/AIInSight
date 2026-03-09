/**
 * Renderer Service
 * Headless browser service that loads a self-contained render bundle and executes card render functions.
 *
 * Endpoints:
 *   POST /render/:type   — render a card, body = payload JSON
 *   GET  /healthz        — health check
 *
 * Environment variables:
 *   RENDER_APP_URL — Optional override for the hosted render bundle URL
 *   PORT          — listen port (default: 3001)
 */

import express from 'express'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const PORT = parseInt(process.env.PORT || '3001', 10)
const RENDER_ROUTE = '/render.html'   // separate entry point for headless rendering
const PAGE_TIMEOUT = 30_000          // ms to wait for page ready
const RENDER_TIMEOUT = 20_000        // ms per render call
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DIST_DIR = path.join(__dirname, 'dist')
const RENDER_APP_URL = process.env.RENDER_APP_URL || `http://127.0.0.1:${PORT}`

let browser = null
let context = null

async function initBrowser() {
  browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })
  context = await browser.newContext({
    viewport: { width: 1120, height: 1500 },
    deviceScaleFactor: 1,
  })
  console.log('[renderer] Browser launched')
}

async function getReadyPage() {
  const page = await context.newPage()
  // Navigate to the self-hosted render bundle
  await page.goto(`${RENDER_APP_URL}${RENDER_ROUTE}`, { waitUntil: 'networkidle', timeout: PAGE_TIMEOUT })
  // Wait for the renderer API to be exposed
  await page.waitForFunction(() => window.__CARD_RENDERER__?.ready === true, { timeout: PAGE_TIMEOUT })
  return page
}

const app = express()
app.use(express.json({ limit: '10mb' }))
app.use(express.static(DIST_DIR))

app.get('/healthz', (_req, res) => {
  res.json({ status: 'ok', browser: !!browser })
})

// Card type mapping
const VALID_TYPES = ['title', 'impact', 'radar', 'timeline', 'trend', 'daily_rank', 'hot_topic']

const TYPE_ALIASES = {
  'daily-rank': 'daily_rank',
  'hot-topic': 'hot_topic',
}

app.post('/render/:type', async (req, res) => {
  const rawType = req.params.type
  const cardType = TYPE_ALIASES[rawType] || rawType

  if (!VALID_TYPES.includes(cardType)) {
    return res.status(400).json({ success: false, error: `Unknown card type: ${rawType}. Valid: ${VALID_TYPES.join(', ')}` })
  }

  let page = null
  try {
    page = await getReadyPage()

    const result = await page.evaluate(async ({ type, payload }) => {
      return await window.__CARD_RENDERER__.render(type, payload)
    }, { type: cardType, payload: req.body })

    res.json({
      success: true,
      image_data_url: result,
      image_url: null,
      width: 1080,
      height: 1440,
      mime_type: 'image/png',
    })
  } catch (err) {
    console.error(`[renderer] Error rendering ${cardType}:`, err.message)
    res.status(500).json({ success: false, error: err.message })
  } finally {
    if (page) await page.close().catch(() => {})
  }
})

// ============================================================
// XHS Login Proxy (Phase 2)
// ============================================================

const XHS_LOGIN_URL = 'https://www.xiaohongshu.com'
const LOGIN_TIMEOUT = 4 * 60 * 1000  // 4 minutes
const LOGIN_POLL_INTERVAL = 2000      // 2 seconds

// API URL for auto-injecting cookies after successful login
const API_BASE_URL = process.env.API_BASE_URL || 'http://api:8000'

// In-memory login sessions
const loginSessions = new Map()

/**
 * Convert Playwright cookies to go-rod compatible format.
 * go-rod's proto.NetworkCookie serializes with lowercase JSON keys
 * (json:"name", json:"value", etc.)
 */
function toGoRodCookies(playwrightCookies) {
  return playwrightCookies.map(c => ({
    name: c.name,
    value: c.value,
    domain: c.domain,
    path: c.path,
    expires: c.expires > 0 ? c.expires : -1,
    size: (c.name || '').length + (c.value || '').length,
    httpOnly: c.httpOnly || false,
    secure: c.secure || false,
    session: !(c.expires > 0),
    priority: 'Medium',
    sameParty: false,
    sourceScheme: c.secure ? 'Secure' : 'NonSecure',
    sourcePort: c.secure ? 443 : 80,
  }))
}

/**
 * Check if cookies contain a valid web_session.
 */
function hasWebSession(cookies) {
  return cookies.some(c => c.name === 'web_session' && c.value)
}

/**
 * Auto-inject cookies to the API backend after successful login.
 * This removes the need for manual polling.
 */
async function autoInjectCookies(sessionId, goRodCookies) {
  const url = `${API_BASE_URL}/api/xhs/upload-cookies`
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cookies: goRodCookies }),
    })
    const data = await resp.json()
    if (data.success) {
      console.log(`[login-xhs] Session ${sessionId}: cookies auto-injected to API ✅`)
    } else {
      console.error(`[login-xhs] Session ${sessionId}: auto-inject failed: ${data.message}`)
    }
  } catch (err) {
    console.error(`[login-xhs] Session ${sessionId}: auto-inject error: ${err.message}`)
  }
}

/**
 * POST /login-xhs
 *
 * Start a Playwright login session:
 * 1. Open xiaohongshu.com in a fresh browser context
 * 2. Wait for the QR code to appear
 * 3. Screenshot it and return base64 + session_id
 * 4. Background-poll for login completion (cookie appearance)
 */
app.post('/login-xhs', async (_req, res) => {
  let loginContext = null
  let page = null

  try {
    // Create isolated context (no shared state with render context)
    loginContext = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      locale: 'zh-CN',
    })

    page = await loginContext.newPage()
    await page.goto(XHS_LOGIN_URL, { waitUntil: 'networkidle', timeout: 30000 })

    // XHS shows a login modal with img.qrcode-img on first visit.
    // Wait for the QR image to actually load (src is a base64 data URL, async).
    let qrElement = null
    try {
      // Primary: wait for img.qrcode-img with a non-empty src and rendered pixels
      qrElement = await page.waitForFunction(() => {
        const img = document.querySelector('img.qrcode-img')
        return img && img.src && img.naturalWidth > 64 ? img : null
      }, { timeout: 15000 })
      // waitForFunction returns a JSHandle; convert to ElementHandle
      qrElement = qrElement.asElement()
    } catch {
      console.log('[login-xhs] img.qrcode-img not ready, trying fallback selectors')
    }

    // Fallback selectors
    if (!qrElement) {
      try {
        qrElement = await page.waitForSelector(
          'div.qrcode img, canvas.qrcode, img[src*="qrcode"]',
          { timeout: 8000 }
        )
      } catch {
        console.log('[login-xhs] QR fallback selectors failed, screenshotting login modal')
      }
    }

    // Screenshot the QR code (or the whole login modal)
    let screenshotBuffer
    if (qrElement) {
      screenshotBuffer = await qrElement.screenshot({ type: 'png' })
    } else {
      // Last resort: screenshot the login modal container
      const modal = await page.$('div.login-container') || await page.$('div.login-modal')
      if (modal) {
        screenshotBuffer = await modal.screenshot({ type: 'png' })
      } else {
        screenshotBuffer = await page.screenshot({ type: 'png', fullPage: false })
      }
    }

    const qrBase64 = screenshotBuffer.toString('base64')
    const sessionId = Math.random().toString(36).slice(2) + Date.now().toString(36)

    // Store session
    const session = {
      id: sessionId,
      status: 'pending',       // pending | logged_in | expired
      context: loginContext,
      page,
      cookies: null,
      createdAt: Date.now(),
    }
    loginSessions.set(sessionId, session)

    // Background polling for login completion
    const pollLogin = async () => {
      const deadline = Date.now() + LOGIN_TIMEOUT
      while (Date.now() < deadline) {
        await new Promise(r => setTimeout(r, LOGIN_POLL_INTERVAL))

        const s = loginSessions.get(sessionId)
        if (!s || s.status !== 'pending') break

        try {
          const cookies = await s.context.cookies()
          if (hasWebSession(cookies)) {
            s.status = 'logged_in'
            s.cookies = toGoRodCookies(cookies)
            console.log(`[login-xhs] Session ${sessionId}: login detected, ${cookies.length} cookies`)
            autoInjectCookies(sessionId, s.cookies)
            break
          }

          // Also check URL change (redirect after scan)
          const url = s.page.url()
          if (url.includes('/user/profile') || url.includes('/explore')) {
            const finalCookies = await s.context.cookies()
            s.status = 'logged_in'
            s.cookies = toGoRodCookies(finalCookies)
            console.log(`[login-xhs] Session ${sessionId}: login detected via URL redirect`)
            autoInjectCookies(sessionId, s.cookies)
            break
          }
        } catch (err) {
          console.error(`[login-xhs] Poll error for ${sessionId}:`, err.message)
          break
        }
      }

      // Mark expired if still pending
      const s = loginSessions.get(sessionId)
      if (s && s.status === 'pending') {
        s.status = 'expired'
        console.log(`[login-xhs] Session ${sessionId}: expired`)
      }

      // Cleanup after a delay (keep data available for final poll)
      setTimeout(() => {
        const s = loginSessions.get(sessionId)
        if (s) {
          s.context.close().catch(() => {})
          loginSessions.delete(sessionId)
          console.log(`[login-xhs] Session ${sessionId}: cleaned up`)
        }
      }, 30000)
    }
    pollLogin().catch(err => console.error('[login-xhs] Poll fatal:', err))

    res.json({
      success: true,
      session_id: sessionId,
      qr_image_data: qrBase64,
      message: '请使用小红书 App 在 4 分钟内扫码登录 👇',
    })
  } catch (err) {
    console.error('[login-xhs] Start error:', err.message)
    if (page) await page.close().catch(() => {})
    if (loginContext) await loginContext.close().catch(() => {})
    res.status(500).json({ success: false, message: err.message })
  }
})

/**
 * GET /login-xhs/status/:sessionId
 *
 * Poll login status for a session.
 * Returns: { status: "pending"|"logged_in"|"expired", cookies?: [...] }
 */
app.get('/login-xhs/status/:sessionId', (req, res) => {
  const session = loginSessions.get(req.params.sessionId)

  if (!session) {
    return res.json({ status: 'expired', message: '会话不存在或已过期' })
  }

  const result = { status: session.status }

  if (session.status === 'logged_in' && session.cookies) {
    result.cookies = session.cookies
  }

  if (session.status === 'pending') {
    result.elapsed_seconds = Math.floor((Date.now() - session.createdAt) / 1000)
  }

  res.json(result)
})

// Start
async function main() {
  await initBrowser()
  app.listen(PORT, () => {
    console.log(`[renderer] Listening on http://0.0.0.0:${PORT}`)
    console.log(`[renderer] Render app URL: ${RENDER_APP_URL}`)
    console.log(`[renderer] XHS login proxy: enabled`)
  })
}

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('[renderer] Shutting down...')
  if (browser) await browser.close()
  process.exit(0)
})

process.on('SIGTERM', async () => {
  if (browser) await browser.close()
  process.exit(0)
})

main().catch(err => {
  console.error('[renderer] Fatal:', err)
  process.exit(1)
})
