/**
 * Action Card Renderer
 * Turns analysis into practical next steps and guardrails.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
  normalizeTags,
  normalizeTextList,
  wrapMixedText,
} from './editorial_helpers.js'

function drawBulletColumn(ctx, {
  title,
  items,
  x,
  y,
  width,
  height,
  colors,
  accent = false,
}) {
  ctx.fillStyle = accent ? colors.panelStrong : colors.panelMuted
  drawRoundedRect(ctx, x, y, width, height, 30)

  ctx.fillStyle = colors.ink
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText(title, x + 28, y + 48)

  let currentY = y + 104
  normalizeTextList(items, 4).forEach((item) => {
    ctx.fillStyle = accent ? colors.accent : colors.ink
    ctx.beginPath()
    ctx.arc(x + 32, currentY - 10, 7, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = colors.ink
    ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const lines = wrapMixedText(ctx, item, width - 76, 3)
    lines.forEach((line, index) => {
      ctx.fillText(line, x + 50, currentY + index * 34)
    })
    currentY += lines.length * 34 + 30
  })
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.strategy
 * @param {string[]} payload.actions
 * @param {string[]} payload.watchouts
 * @param {string} payload.audience
 * @param {string[]} payload.tags
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderActionCard({
  title = '',
  strategy = '',
  actions = [],
  watchouts = [],
  audience = '',
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
    section: 'WHAT TO DO',
    title: '接下来怎么做',
    subtitle: audience || '把判断落成动作，也把风险写清楚',
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 392, 924, 184, 34)

  ctx.fillStyle = colors.accent
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('执行策略', 110, 446)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 42px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const strategyLines = wrapMixedText(
    ctx,
    strategy || normalizeTextList(actions, 1)[0] || title || '先试小范围，再看关键风险是否被压住。',
    840,
    3,
  )
  strategyLines.forEach((line, index) => {
    ctx.fillText(line, 110, 516 + index * 48)
  })

  drawBulletColumn(ctx, {
    title: '立刻做',
    items: actions.length > 0 ? actions : ['先给这个话题设一个可验证的小范围实验。'],
    x: 78,
    y: 614,
    width: 444,
    height: 548,
    colors,
    accent: true,
  })
  drawBulletColumn(ctx, {
    title: '重点盯',
    items: watchouts.length > 0 ? watchouts : ['别把热点热度误判成长期确定性。'],
    x: 556,
    y: 614,
    width: 446,
    height: 548,
    colors,
    accent: false,
  })

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 78, 1186, 924, 116, 24)

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('适用对象', 110, 1236)

  ctx.fillStyle = colors.ink
  const audienceText = audience || '个人用户 / 开发者 / 企业负责人'
  const chips = normalizeTags(tags, 3)
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const chipWidths = chips.map((label) => Math.min(ctx.measureText(label).width + 30, 160))
  const totalChipWidth = chipWidths.reduce((sum, width) => sum + width, 0) + Math.max(chipWidths.length - 1, 0) * 10
  const chipStartX = Math.max(560, 970 - totalChipWidth)
  const audienceWidth = Math.max(chipStartX - 246, 230)
  ctx.font = 'bold 24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const audienceLines = wrapMixedText(ctx, audienceText, audienceWidth, 2)
  audienceLines.forEach((line, index) => {
    ctx.fillText(line, 220, 1238 + index * 28)
  })

  let chipX = chipStartX
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  chips.forEach((label, index) => {
    const width = chipWidths[index]
    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, chipX, 1222, width, 44, 22)
    ctx.fillStyle = '#ffffff'
    ctx.textBaseline = 'middle'
    ctx.fillText(fitTextWithEllipsis(ctx, label, width - 20), chipX + 14, 1244)
    chipX += width + 10
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('AIINSIGHT / ACTION CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
