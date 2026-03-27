export const editorialPalette = {
  gradientStart: '#fbf4e3',
  gradientMid: '#f4e2c6',
  gradientEnd: '#ead2b1',
  ink: '#6f2500',
  accent: '#ff7a00',
  accentSoft: '#ffd28b',
  panel: 'rgba(255, 248, 235, 0.82)',
  panelStrong: 'rgba(255, 251, 245, 0.92)',
  panelMuted: 'rgba(255, 255, 255, 0.58)',
  line: 'rgba(111, 37, 0, 0.12)',
  glow: 'rgba(255, 167, 79, 0.28)',
  subtleText: '#a9704c',
  paleInk: '#b98964',
}

export function drawRoundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
  ctx.fill()
}

export function drawStrokeRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
  ctx.stroke()
}

export function drawSoftGlow(ctx, x, y, radius, color) {
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)
  gradient.addColorStop(0, color)
  gradient.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, Math.PI * 2)
  ctx.fill()
}

export function drawGrid(ctx, width, height, color) {
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

function tokenizeMixedText(text) {
  const source = (text || '').trim()
  if (!source) return ['']

  const raw = source.match(/[\u4e00-\u9fff]|[A-Za-z0-9.+/#&-]+|[^\sA-Za-z0-9\u4e00-\u9fff]+|\s+/g) || [source]
  return raw.map((token) => (/\s+/.test(token) ? ' ' : token))
}

export function wrapMixedText(ctx, text, maxWidth, maxLines = 4) {
  const tokens = tokenizeMixedText(text)
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

  if (lines.length > maxLines) lines.length = maxLines

  for (let i = 1; i < lines.length; i += 1) {
    const punctuation = lines[i].match(/^[，。！？；：、,.!?）】》」』]+/)
    if (punctuation) {
      lines[i - 1] += punctuation[0]
      lines[i] = lines[i].slice(punctuation[0].length).trimStart()
    }
  }

  const compactLines = lines.filter(Boolean)

  const consumed = compactLines.join(' ')
  if (consumed.length < (text || '').trim().length && lines.length > 0) {
    let clipped = compactLines[compactLines.length - 1].replace(/[ ,.;:!?\-_/]*$/, '')
    while (clipped.length > 1 && ctx.measureText(`${clipped}…`).width > maxWidth) {
      clipped = clipped.slice(0, -1)
    }
    compactLines[compactLines.length - 1] = `${clipped}…`
  }

  return compactLines.length > 0 ? compactLines : ['']
}

export function fitTextWithEllipsis(ctx, text, maxWidth) {
  const source = (text || '').trim()
  if (!source) return ''
  if (ctx.measureText(source).width <= maxWidth) return source

  let output = source
  while (output.length > 1 && ctx.measureText(`${output}…`).width > maxWidth) {
    output = output.slice(0, -1)
  }
  return `${output}…`
}

function normalizeObjectText(item) {
  if (!item || typeof item !== 'object') return ''

  const primary = [
    item.label,
    item.title,
    item.claim,
    item.summary,
    item.event,
    item.headline,
    item.name,
  ].find((value) => typeof value === 'string' && value.trim())

  const secondary = [
    item.desc,
    item.detail,
    item.reason,
    item.source,
    item.value,
    item.time,
    item.note,
  ].find((value) => typeof value === 'string' && value.trim())

  if (primary && secondary && secondary !== primary) {
    return `${primary} · ${secondary}`
  }
  return primary || secondary || ''
}

export function normalizeTextItem(item) {
  if (typeof item === 'string') return item.trim()
  if (typeof item === 'number') return String(item)
  return normalizeObjectText(item)
}

export function normalizeTextList(items, max = 5) {
  return (items || [])
    .map(normalizeTextItem)
    .filter(Boolean)
    .slice(0, max)
}

export function formatConfidenceValue(confidence) {
  if (confidence === null || confidence === undefined || confidence === '') return ''

  if (typeof confidence === 'number') {
    const normalized = confidence <= 1 ? confidence * 100 : confidence
    return `${Math.round(normalized)}%`
  }

  const value = String(confidence).trim()
  if (!value) return ''

  const asNumber = Number(value)
  if (!Number.isNaN(asNumber)) {
    const normalized = asNumber <= 1 ? asNumber * 100 : asNumber
    return `${Math.round(normalized)}%`
  }
  return value
}

export function splitSummaryIntoBullets(summary, maxBullets = 3) {
  const source = (summary || '').trim()
  if (!source) return ['暂无摘要，建议先补充分析结果后再发布。']

  const pieces = source
    .split(/[。！？!?；;\n]/)
    .map((item) => item.trim())
    .filter(Boolean)

  if (pieces.length > 0) return pieces.slice(0, maxBullets)

  const fallback = []
  for (let i = 0; i < source.length && fallback.length < maxBullets; i += 24) {
    fallback.push(source.slice(i, i + 24))
  }
  return fallback
}

export function normalizeTags(tags, max = 5) {
  return (tags || []).filter(Boolean).slice(0, max).map((tag) => (tag.startsWith('#') ? tag : `#${tag}`))
}

export function drawOrbitalMotif(ctx, x, y, colors = editorialPalette, scale = 1) {
  ctx.save()
  ctx.translate(x, y)
  ctx.scale(scale, scale)

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

export function drawEditorialScaffold(ctx, width, height, colors = editorialPalette) {
  const bg = ctx.createLinearGradient(0, 0, width, height)
  bg.addColorStop(0, colors.gradientStart)
  bg.addColorStop(0.55, colors.gradientMid)
  bg.addColorStop(1, colors.gradientEnd)
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, width, height)

  drawSoftGlow(ctx, width - 150, 170, 220, colors.glow)
  drawSoftGlow(ctx, 180, height - 220, 220, colors.glow)
  drawGrid(ctx, width, height, colors.line)

  ctx.strokeStyle = colors.line
  ctx.lineWidth = 2
  drawStrokeRect(ctx, 36, 36, width - 72, height - 72, 38)

  ctx.fillStyle = colors.panel
  drawRoundedRect(ctx, 54, 54, width - 108, height - 108, 34)
}

export function drawEditorialHeader(
  ctx,
  {
    width,
    date = '',
    section = 'EDITORIAL',
    title = '',
    subtitle = '',
    colors = editorialPalette,
    motifScale = 0.72,
    titleWidth = 620,
    titleFont = 74,
  },
) {
  ctx.fillStyle = colors.ink
  drawRoundedRect(ctx, 92, 88, 182, 48, 24)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('AI DAILY', 183, 112)

  ctx.fillStyle = colors.subtleText
  ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText(section, 304, 112)

  if (date) {
    ctx.textAlign = 'right'
    ctx.fillText(date, width - 94, 112)
  }

  drawOrbitalMotif(ctx, width - 220, 200, colors, motifScale)

  ctx.fillStyle = colors.accent
  drawRoundedRect(ctx, 92, 188, 18, 134, 9)
  drawRoundedRect(ctx, 128, 210, 12, 92, 6)

  ctx.fillStyle = colors.ink
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'

  let size = titleFont
  let lines = []
  for (; size >= 54; size -= 4) {
    ctx.font = `900 ${size}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    lines = wrapMixedText(ctx, title || '', titleWidth, 2)
    if (lines.length <= 2) break
  }
  if (lines.length === 0) lines = ['']

  const lineHeight = size * 1.06
  lines.forEach((line, index) => {
    ctx.fillText(line, 92, 250 + index * lineHeight)
  })
  const titleBottom = 250 + (lines.length - 1) * lineHeight

  if (subtitle) {
    ctx.fillStyle = colors.subtleText
    ctx.font = '28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(subtitle, 92, titleBottom + 58)
  }

  return {
    titleBottom,
    subtitleBottom: subtitle ? titleBottom + 58 : titleBottom,
    titleSize: size,
    titleLines: lines,
  }
}
