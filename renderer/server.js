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
const VALID_TYPES = ['title', 'radar', 'timeline', 'trend', 'daily_rank', 'hot_topic']

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

// Start
async function main() {
  await initBrowser()
  app.listen(PORT, () => {
    console.log(`[renderer] Listening on http://0.0.0.0:${PORT}`)
    console.log(`[renderer] Render app URL: ${RENDER_APP_URL}`)
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
