/**
 * Impact Card Renderer
 * Editorial "why it matters / what to watch" card for topic deep dives.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
  normalizeTags,
  wrapMixedText,
} from './editorial_helpers.js'

function drawBulletList(ctx, items, x, y, width, lineHeight, colors) {
  let currentY = y
  items.forEach((item) => {
    ctx.fillStyle = colors.accent
    ctx.beginPath()
    ctx.arc(x, currentY - 8, 7, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = colors.ink
    ctx.font = '30px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const lines = wrapMixedText(ctx, item, width, 2)
    lines.forEach((line, index) => {
      ctx.fillText(line, x + 22, currentY + index * lineHeight)
    })
    currentY += lines.length * lineHeight + 28
  })
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.summary
 * @param {string} payload.insight
 * @param {string[]} payload.signals
 * @param {string[]} payload.actions
 * @param {string} payload.confidence
 * @param {string[]} payload.tags
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderImpactCard({
  title = '',
  summary = '',
  insight = '',
  signals = [],
  actions = [],
  confidence = '',
  tags = [],
}) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'WHAT TO DO NEXT',
    title: '影响判断与跟进',
    subtitle: confidence ? `当前结论成熟度：${confidence}` : '聚焦为什么重要、下一步怎么跟',
    colors,
    motifScale: 0.72,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 384, 924, 246, 34)

  ctx.fillStyle = colors.accent
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('一句话判断', 110, 436)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 48px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const summaryLines = wrapMixedText(ctx, summary || title || '值得继续跟进', 840, 3)
  summaryLines.forEach((line, index) => {
    ctx.fillText(line, 110, 510 + index * 56)
  })

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 78, 658, 444, 522, 30)
  drawRoundedRect(ctx, 556, 658, 446, 522, 30)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 30px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('为什么重要', 112, 708)
  ctx.fillText('接下来怎么看', 590, 708)

  drawBulletList(ctx, signals.slice(0, 3), 118, 778, 338, 40, colors)
  drawBulletList(ctx, actions.slice(0, 3), 596, 778, 338, 40, colors)

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 1212, 924, 96, 28)

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('内容切角', 112, 1268)

  const chipLabels = normalizeTags(tags, 4)
  let chipX = 220
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  chipLabels.forEach((label) => {
    const chipWidth = Math.min(ctx.measureText(label).width + 28, 180)
    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, chipX, 1232, chipWidth, 52, 24)
    ctx.fillStyle = '#ffffff'
    ctx.textBaseline = 'middle'
    ctx.fillText(fitTextWithEllipsis(ctx, label, chipWidth - 22), chipX + 14, 1258)
    chipX += chipWidth + 12
  })

  if (chipLabels.length === 0) {
    ctx.fillStyle = colors.ink
    ctx.fillText('这张卡适合放在封面后，承接“为什么值得讲”', 220, 1268)
  }

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('AIINSIGHT / IMPACT CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('Preview Card', WIDTH - 108, HEIGHT - 86)

  if (insight) {
    ctx.textAlign = 'left'
    ctx.fillStyle = colors.paleInk
    ctx.font = '22px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const insightLines = wrapMixedText(ctx, insight, 860, 2)
    insightLines.forEach((line, index) => {
      ctx.fillText(line, 110, 602 + index * 28)
    })
  }

  return canvas.toDataURL('image/png')
}
