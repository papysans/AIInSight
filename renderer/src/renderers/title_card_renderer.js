/**
 * Title Card Renderer
 * Editorial-style cover for Xiaohongshu previews.
 * Output: 1080×1440 PNG base64 DataURL
 */

const themeColorMap = {
  warm: {
    gradientStart: '#fbf4e3',
    gradientMid: '#f4e2c6',
    gradientEnd: '#ead2b1',
    ink: '#6f2500',
    accent: '#ff7a00',
    accentSoft: '#ffd28b',
    panel: 'rgba(255, 248, 235, 0.82)',
    line: 'rgba(111, 37, 0, 0.12)',
    glow: 'rgba(255, 167, 79, 0.28)',
  },
  peach: {
    gradientStart: '#fff1ec',
    gradientMid: '#ffd9cc',
    gradientEnd: '#ffc6b2',
    ink: '#742a1d',
    accent: '#ff6b4a',
    accentSoft: '#ffc19e',
    panel: 'rgba(255, 247, 243, 0.82)',
    line: 'rgba(116, 42, 29, 0.12)',
    glow: 'rgba(255, 107, 74, 0.22)',
  },
  sunset: {
    gradientStart: '#fff0d6',
    gradientMid: '#ffd8bf',
    gradientEnd: '#ffc9cf',
    ink: '#7a2900',
    accent: '#ff5d3d',
    accentSoft: '#ffd59a',
    panel: 'rgba(255, 249, 240, 0.82)',
    line: 'rgba(122, 41, 0, 0.1)',
    glow: 'rgba(255, 93, 61, 0.22)',
  },
  cool: {
    gradientStart: '#eef4ff',
    gradientMid: '#dbeafe',
    gradientEnd: '#d4f4ff',
    ink: '#16233b',
    accent: '#2563eb',
    accentSoft: '#93c5fd',
    panel: 'rgba(247, 251, 255, 0.8)',
    line: 'rgba(22, 35, 59, 0.12)',
    glow: 'rgba(37, 99, 235, 0.18)',
  },
  ocean: {
    gradientStart: '#e8f6ff',
    gradientMid: '#d3efff',
    gradientEnd: '#c9f7f0',
    ink: '#103268',
    accent: '#0077ff',
    accentSoft: '#7dd3fc',
    panel: 'rgba(245, 252, 255, 0.8)',
    line: 'rgba(16, 50, 104, 0.12)',
    glow: 'rgba(0, 119, 255, 0.18)',
  },
  mint: {
    gradientStart: '#f0fff7',
    gradientMid: '#ddfaee',
    gradientEnd: '#cdf5e4',
    ink: '#104536',
    accent: '#10b981',
    accentSoft: '#86efac',
    panel: 'rgba(247, 255, 250, 0.8)',
    line: 'rgba(16, 69, 54, 0.11)',
    glow: 'rgba(16, 185, 129, 0.18)',
  },
  sky: {
    gradientStart: '#eef8ff',
    gradientMid: '#deefff',
    gradientEnd: '#d8e8ff',
    ink: '#11385e',
    accent: '#0ea5e9',
    accentSoft: '#7dd3fc',
    panel: 'rgba(247, 251, 255, 0.82)',
    line: 'rgba(17, 56, 94, 0.11)',
    glow: 'rgba(14, 165, 233, 0.18)',
  },
  lavender: {
    gradientStart: '#faf5ff',
    gradientMid: '#efe3ff',
    gradientEnd: '#e8dcff',
    ink: '#4c1d95',
    accent: '#8b5cf6',
    accentSoft: '#c4b5fd',
    panel: 'rgba(252, 248, 255, 0.82)',
    line: 'rgba(76, 29, 149, 0.1)',
    glow: 'rgba(139, 92, 246, 0.18)',
  },
  grape: {
    gradientStart: '#f8f0ff',
    gradientMid: '#efe1ff',
    gradientEnd: '#f7dcff',
    ink: '#561b83',
    accent: '#a855f7',
    accentSoft: '#e9d5ff',
    panel: 'rgba(252, 248, 255, 0.82)',
    line: 'rgba(86, 27, 131, 0.1)',
    glow: 'rgba(168, 85, 247, 0.18)',
  },
  forest: {
    gradientStart: '#f3fff6',
    gradientMid: '#def8e7',
    gradientEnd: '#cfead8',
    ink: '#12452b',
    accent: '#16a34a',
    accentSoft: '#86efac',
    panel: 'rgba(248, 255, 250, 0.82)',
    line: 'rgba(18, 69, 43, 0.11)',
    glow: 'rgba(22, 163, 74, 0.16)',
  },
  lime: {
    gradientStart: '#fbffe6',
    gradientMid: '#eef8bf',
    gradientEnd: '#e2f2ab',
    ink: '#3f4c08',
    accent: '#65a30d',
    accentSoft: '#d9f99d',
    panel: 'rgba(252, 255, 245, 0.82)',
    line: 'rgba(63, 76, 8, 0.11)',
    glow: 'rgba(101, 163, 13, 0.16)',
  },
  alert: {
    gradientStart: '#fff1f2',
    gradientMid: '#ffd6d8',
    gradientEnd: '#ffc6d1',
    ink: '#7f1d1d',
    accent: '#ef4444',
    accentSoft: '#fda4af',
    panel: 'rgba(255, 246, 247, 0.82)',
    line: 'rgba(127, 29, 29, 0.11)',
    glow: 'rgba(239, 68, 68, 0.18)',
  },
  dark: {
    gradientStart: '#172033',
    gradientMid: '#0f172a',
    gradientEnd: '#08111f',
    ink: '#ffffff',
    accent: '#38bdf8',
    accentSoft: '#60a5fa',
    panel: 'rgba(15, 23, 42, 0.62)',
    line: 'rgba(255, 255, 255, 0.1)',
    glow: 'rgba(56, 189, 248, 0.18)',
  },
  cream: {
    gradientStart: '#fffaf2',
    gradientMid: '#f9eed7',
    gradientEnd: '#f0dfbf',
    ink: '#3b2d1c',
    accent: '#d97706',
    accentSoft: '#fed7aa',
    panel: 'rgba(255, 249, 240, 0.82)',
    line: 'rgba(59, 45, 28, 0.1)',
    glow: 'rgba(217, 119, 6, 0.16)',
  },
}

function drawRoundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
  ctx.fill()
}

function drawStrokeRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
  ctx.stroke()
}

function drawSoftGlow(ctx, x, y, radius, color) {
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)
  gradient.addColorStop(0, color)
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, Math.PI * 2)
  ctx.fill()
}

function drawGrid(ctx, width, height, color) {
  ctx.save()
  ctx.strokeStyle = color
  ctx.lineWidth = 1
  ctx.globalAlpha = 0.4
  for (let x = 72; x < width - 72; x += 72) {
    ctx.beginPath()
    ctx.moveTo(x, 64)
    ctx.lineTo(x, height - 64)
    ctx.stroke()
  }
  for (let y = 64; y < height - 64; y += 72) {
    ctx.beginPath()
    ctx.moveTo(64, y)
    ctx.lineTo(width - 64, y)
    ctx.stroke()
  }
  ctx.restore()
}

function tokenizeTitle(text) {
  const source = (text || '').trim()
  if (!source) return ['标题生成中...']

  const raw = source.match(/[\u4e00-\u9fff]|[A-Za-z0-9.+/#&-]+|[^\sA-Za-z0-9\u4e00-\u9fff]+|\s+/g) || [source]
  return raw.map((token) => (/\s+/.test(token) ? ' ' : token))
}

function wrapTitle(ctx, title, maxWidth, maxLines) {
  const tokens = tokenizeTitle(title)
  const lines = []
  let current = ''

  const pushCurrent = () => {
    if (current.trim()) lines.push(current.trim())
    current = ''
  }

  for (const token of tokens) {
    if (token === ' ') {
      if (current && !current.endsWith(' ')) current += ' '
      continue
    }

    const candidate = current ? `${current}${token}` : token
    if (ctx.measureText(candidate).width <= maxWidth || !current) {
      current = candidate
      continue
    }

    pushCurrent()
    current = token

    if (lines.length === maxLines - 1) break
  }

  pushCurrent()

  if (lines.length > maxLines) {
    lines.length = maxLines
  }

  const consumed = lines.join(' ')
  if (consumed.length < (title || '').trim().length) {
    const last = lines[lines.length - 1] || ''
    let clipped = last.replace(/[ ,.;:!?\-_/]*$/, '')
    while (clipped.length > 1 && ctx.measureText(`${clipped}…`).width > maxWidth) {
      clipped = clipped.slice(0, -1)
    }
    lines[lines.length - 1] = `${clipped}…`
  }

  return lines
}

function extractKeywords(title) {
  const tokens = (title || '').match(/[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9.+/#&-]*/g) || []
  const stopwords = new Set(['for', 'the', 'and', 'with', 'from', 'into', 'that', 'this', 'will', 'are', 'agent'])
  const seen = new Set()
  const keywords = []

  for (const token of tokens) {
    const key = token.toLowerCase()
    if (seen.has(key) || stopwords.has(key) || token.length < 2) continue
    seen.add(key)
    keywords.push(token)
    if (keywords.length >= 3) break
  }

  return keywords.length > 0 ? keywords : ['AI热点', '今日话题']
}

function inferLabel(title) {
  const text = (title || '').toLowerCase()
  if (/(paper|research|arxiv|论文|研究)/.test(text)) return 'RESEARCH SIGNAL'
  if (/(agent|workflow|copilot|assistant)/.test(text)) return 'AGENT STACK'
  if (/(gpt|claude|model|llm|deepseek|qwen|gemini)/.test(text)) return 'MODEL WATCH'
  if (/(launch|release|open source|开源|发布|上线)/.test(text)) return 'PRODUCT DROP'
  return 'AI DAILY COVER'
}

function splitTitleMeta(title) {
  const source = (title || '').trim()
  if (!source) return { headline: '标题生成中...', meta: '' }

  const separators = ['｜', '|', '·']
  for (const separator of separators) {
    if (!source.includes(separator)) continue
    const [headline, ...rest] = source.split(separator)
    const meta = rest.join(separator).trim()
    return {
      headline: headline.trim() || source,
      meta,
    }
  }

  return { headline: source, meta: '' }
}

function isDateLikeText(text) {
  return /(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}月\d{1,2}日)/.test(text || '')
}

function formatHeaderDateLines(raw) {
  const value = (raw || '').trim()
  if (!value) return []

  const isoMatch = value.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/)
  if (isoMatch) {
    const [, year, month, day] = isoMatch
    return [year, `${month.padStart(2, '0')}-${day.padStart(2, '0')}`]
  }

  const cnMatch = value.match(/^(\d{1,2})月(\d{1,2})日$/)
  if (cnMatch) {
    const [, month, day] = cnMatch
    return [`${month}月`, `${day}日`]
  }

  return [value]
}

function drawOrbitalMotif(ctx, x, y, colors) {
  ctx.save()
  ctx.translate(x, y)

  ctx.strokeStyle = colors.line
  ctx.lineWidth = 4
  ctx.beginPath()
  ctx.arc(0, 0, 118, 0, Math.PI * 2)
  ctx.stroke()

  ctx.globalAlpha = 0.9
  ctx.strokeStyle = colors.accent
  ctx.lineWidth = 10
  ctx.beginPath()
  ctx.arc(0, 0, 146, Math.PI * 0.16, Math.PI * 0.82)
  ctx.stroke()

  ctx.strokeStyle = colors.ink
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.arc(0, 0, 182, Math.PI * 1.1, Math.PI * 1.8)
  ctx.stroke()

  ctx.fillStyle = colors.ink
  ctx.beginPath()
  ctx.arc(0, 0, 14, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = colors.accent
  ctx.beginPath()
  ctx.arc(140, 34, 18, 0, Math.PI * 2)
  ctx.fill()

  ctx.globalAlpha = 0.65
  ctx.fillStyle = colors.accentSoft
  drawRoundedRect(ctx, -90, 138, 182, 28, 14)
  drawRoundedRect(ctx, -90, 182, 236, 18, 9)
  drawRoundedRect(ctx, -90, 216, 140, 18, 9)
  ctx.restore()
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} [payload.emoji='🤔']
 * @param {string} [payload.theme='cool']
 * @param {string} [payload.emojiPos='bottom-right']
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderTitleCard({ title, emoji = '🤔', theme = 'cool', emojiPos = 'bottom-right' }) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')

  const colors = themeColorMap[theme] || themeColorMap.cool

  const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT)
  gradient.addColorStop(0, colors.gradientStart)
  gradient.addColorStop(0.5, colors.gradientMid || colors.gradientStart)
  gradient.addColorStop(1, colors.gradientEnd)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, WIDTH, HEIGHT)

  drawSoftGlow(ctx, 920, 210, 250, colors.glow)
  drawSoftGlow(ctx, 180, 1250, 220, colors.glow)
  drawGrid(ctx, WIDTH, HEIGHT, colors.line)

  ctx.strokeStyle = colors.line
  ctx.lineWidth = 2
  drawStrokeRect(ctx, 36, 36, WIDTH - 72, HEIGHT - 72, 38)

  ctx.fillStyle = colors.panel
  drawRoundedRect(ctx, 54, 54, WIDTH - 108, HEIGHT - 108, 34)

  ctx.fillStyle = colors.ink
  drawRoundedRect(ctx, 92, 88, 182, 48, 24)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 24px "SF Pro Display", "PingFang SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('AI DAILY', 183, 112)

  ctx.fillStyle = colors.ink
  ctx.globalAlpha = 0.7
  ctx.font = '26px "SF Pro Display", "PingFang SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText(inferLabel(title), 304, 112)
  ctx.globalAlpha = 1

  const { headline: headlineText, meta: metaText } = splitTitleMeta(title)
  const today = new Date().toISOString().slice(0, 10)
  const headerDateLines = formatHeaderDateLines(isDateLikeText(metaText) ? metaText : today)
  ctx.fillStyle = colors.ink
  ctx.globalAlpha = 0.56
  ctx.textAlign = 'right'
  ctx.textBaseline = 'alphabetic'
  ctx.font = '20px "SF Pro Display", "PingFang SC", sans-serif'
  headerDateLines.forEach((line, index) => {
    ctx.fillText(line, WIDTH - 94, 104 + index * 24)
  })
  ctx.globalAlpha = 1

  ctx.fillStyle = colors.accent
  drawRoundedRect(ctx, 92, 180, 18, 164, 9)
  drawRoundedRect(ctx, 128, 204, 12, 116, 6)

  drawOrbitalMotif(ctx, 860, 300, colors)

  const titleWidth = 760
  let fontSize = 108
  let lines = []

  for (; fontSize >= 74; fontSize -= 8) {
    ctx.font = `900 ${fontSize}px "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif`
    lines = wrapTitle(ctx, headlineText, titleWidth, 5)
    const lastLineLength = (lines[lines.length - 1] || '').replace(/\s/g, '').length
    const hasWidowLine = lines.length >= 2 && lastLineLength <= 2
    if ((lines.length <= 4 && !hasWidowLine) || fontSize <= 82) break
  }

  const lineHeight = fontSize * 1.04
  const startX = 92
  const startY = 440

  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = colors.ink
  ctx.shadowColor = 'rgba(255,255,255,0.12)'
  ctx.shadowBlur = 14
  ctx.shadowOffsetX = 0
  ctx.shadowOffsetY = 6
  ctx.font = `900 ${fontSize}px "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif`

  lines.forEach((line, index) => {
    const y = startY + index * lineHeight
    ctx.fillText(line, startX, y)

    if (index === 0) {
      const underlineWidth = Math.min(ctx.measureText(line).width + 28, titleWidth * 0.72)
      ctx.shadowBlur = 0
      ctx.fillStyle = colors.accentSoft
      drawRoundedRect(ctx, startX, y + 18, underlineWidth, 12, 6)
      ctx.fillStyle = colors.ink
      ctx.shadowBlur = 14
    }
  })

  ctx.shadowBlur = 0

  let metaBottomY = startY + lines.length * lineHeight
  if (metaText) {
    const metaFontSize = Math.max(38, Math.floor(fontSize * 0.46))
    ctx.fillStyle = colors.subtleText
    ctx.font = `bold ${metaFontSize}px "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif`
    const metaLines = wrapTitle(ctx, metaText, titleWidth * 0.72, 2)
    metaLines.forEach((line, index) => {
      const y = metaBottomY + 18 + index * (metaFontSize * 1.08)
      ctx.fillText(line, startX, y)
      metaBottomY = y
    })
  }

  const deckY = metaText ? metaBottomY + 68 : startY + lines.length * lineHeight + 72
  ctx.fillStyle = colors.ink
  ctx.globalAlpha = 0.72
  ctx.font = '28px "SF Pro Display", "PingFang SC", sans-serif'
  ctx.fillText('多源热榜筛出的高价值话题', startX, deckY)
  ctx.fillText('适合继续做解读与发布', startX, deckY + 42)
  ctx.globalAlpha = 1

  const keywords = extractKeywords(headlineText)
  const panelY = HEIGHT - 320
  ctx.fillStyle = 'rgba(255,255,255,0.58)'
  drawRoundedRect(ctx, 78, panelY, WIDTH - 156, 176, 34)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", sans-serif'
  ctx.fillText('关键词', 112, panelY + 48)

  let chipX = 112
  const chipY = panelY + 78
  ctx.font = '26px "SF Pro Display", "PingFang SC", sans-serif'
  keywords.forEach((keyword) => {
    const label = keyword.length > 16 ? `${keyword.slice(0, 15)}…` : keyword
    const width = ctx.measureText(label).width + 42
    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, chipX, chipY, width, 46, 23)
    ctx.fillStyle = '#ffffff'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, chipX + 21, chipY + 23)
    chipX += width + 12
  })

  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = colors.ink
  ctx.globalAlpha = 0.8
  ctx.font = '24px "SF Pro Display", "PingFang SC", sans-serif'
  ctx.fillText('AIINSIGHT / AI HOT TOPIC COVER', 112, panelY + 150)

  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 112, panelY + 150)
  ctx.globalAlpha = 1

  ctx.fillStyle = colors.accent
  ctx.globalAlpha = 0.16
  ctx.font = 'bold 240px "SF Pro Display", sans-serif'
  ctx.fillText('AI', WIDTH - 112, HEIGHT - 120)
  ctx.globalAlpha = 1

  return canvas.toDataURL('image/png')
}

export { themeColorMap }
