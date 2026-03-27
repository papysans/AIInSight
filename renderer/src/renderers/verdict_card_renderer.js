/**
 * Verdict Card Renderer
 * Primary editorial conclusion card for topic deep dives.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
  formatConfidenceValue,
  normalizeTags,
  wrapMixedText,
} from './editorial_helpers.js'

function drawBodyCopy(ctx, text, x, y, width, maxLines, lineHeight, colors) {
  const lines = wrapMixedText(ctx, text, width, maxLines)
  ctx.fillStyle = colors.ink
  lines.forEach((line, index) => {
    ctx.fillText(line, x, y + index * lineHeight)
  })
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.verdict
 * @param {string} payload.why_now
 * @param {string|number} payload.confidence
 * @param {string} payload.caveat
 * @param {string} payload.stance
 * @param {string[]} payload.tags
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderVerdictCard({
  title = '',
  verdict = '',
  why_now = '',
  confidence = '',
  caveat = '',
  stance = '',
  tags = [],
}) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  const confidenceLabel = formatConfidenceValue(confidence)

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'CORE VERDICT',
    title: '先给结论',
    subtitle: confidenceLabel
      ? `当前判断置信度：${confidenceLabel}`
      : '先回答值不值得讲，再补充边界',
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 390, 924, 250, 34)

  ctx.fillStyle = colors.accent
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('一句话判断', 110, 446)

  if (stance) {
    const chipText = fitTextWithEllipsis(ctx, stance, 180)
    const chipWidth = Math.min(ctx.measureText(chipText).width + 36, 220)
    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, 1002 - chipWidth, 414, chipWidth, 48, 24)
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 22px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(chipText, 1002 - chipWidth / 2, 438)
  }

  ctx.fillStyle = colors.ink
  ctx.font = '900 48px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  const verdictLines = wrapMixedText(ctx, verdict || title || '判断仍在生成中', 834, 3)
  verdictLines.forEach((line, index) => {
    ctx.fillText(line, 110, 520 + index * 56)
  })

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 78, 672, 444, 424, 30)
  drawRoundedRect(ctx, 556, 672, 446, 424, 30)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 30px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('为什么是现在', 112, 724)
  ctx.fillText('这条判断的边界', 590, 724)

  ctx.fillStyle = colors.subtleText
  ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  drawBodyCopy(
    ctx,
    why_now || '把这件事放到当下看，它已经不是单点新闻，而是趋势信号。',
    112,
    790,
    350,
    6,
    40,
    colors,
  )
  drawBodyCopy(
    ctx,
    caveat || '结论并不等于全面成立，仍要看证据覆盖度和落地条件。',
    590,
    790,
    350,
    6,
    40,
    colors,
  )

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 1128, 924, 154, 30)

  const stats = [
    ['判断立场', fitTextWithEllipsis(ctx, stance || '结论待定', 210)],
    ['置信度', confidenceLabel || '--'],
    ['内容切角', normalizeTags(tags, 2).join(' ') || '趋势 / 争议 / 机会'],
  ]
  stats.forEach(([label, value], index) => {
    const x = 110 + index * 292
    ctx.fillStyle = colors.subtleText
    ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(label, x, 1178)
    ctx.fillStyle = colors.ink
    ctx.font = `bold ${index === 2 ? 24 : 38}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    const maxWidth = index === 2 ? 230 : 220
    ctx.fillText(fitTextWithEllipsis(ctx, value, maxWidth), x, 1238)
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('AIINSIGHT / VERDICT CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
