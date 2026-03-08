/**
 * Hot Topic Card Renderer
 * Editorial detail card aligned with the title cover language.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawGrid,
  drawOrbitalMotif,
  drawRoundedRect,
  drawSoftGlow,
  drawStrokeRect,
  fitTextWithEllipsis,
  normalizeTags,
  splitSummaryIntoBullets,
  wrapMixedText,
} from './editorial_helpers.js'

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.summary
 * @param {string[]} [payload.tags]
 * @param {number} [payload.sourceCount]
 * @param {number} [payload.score]
 * @param {string} [payload.date]
 * @param {string[]} [payload.sources]
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderHotTopicCard({
  title,
  summary,
  tags = [],
  sourceCount = 0,
  score = 0,
  date = '',
  sources = [],
}) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  const bg = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT)
  bg.addColorStop(0, colors.gradientStart)
  bg.addColorStop(0.55, colors.gradientMid)
  bg.addColorStop(1, colors.gradientEnd)
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, WIDTH, HEIGHT)

  drawSoftGlow(ctx, 930, 210, 250, colors.glow)
  drawSoftGlow(ctx, 150, 1240, 210, colors.glow)
  drawGrid(ctx, WIDTH, HEIGHT, colors.line)

  ctx.strokeStyle = colors.line
  ctx.lineWidth = 2
  drawStrokeRect(ctx, 36, 36, WIDTH - 72, HEIGHT - 72, 38)

  ctx.fillStyle = colors.panel
  drawRoundedRect(ctx, 54, 54, WIDTH - 108, HEIGHT - 108, 34)

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
  ctx.fillText('HOT TOPIC BRIEF', 304, 112)

  if (date) {
    ctx.textAlign = 'right'
    ctx.fillText(date, WIDTH - 94, 112)
  }

  ctx.fillStyle = colors.accent
  drawRoundedRect(ctx, 92, 182, 18, 164, 9)
  drawRoundedRect(ctx, 128, 206, 12, 116, 6)

  drawOrbitalMotif(ctx, 855, 268, colors, 0.86)

  const titleText = title || '热点标题'
  let titleSize = 76
  let titleLines = []
  for (; titleSize >= 54; titleSize -= 4) {
    ctx.font = `900 ${titleSize}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    titleLines = wrapMixedText(ctx, titleText, 610, 5)
    if (titleLines.length <= 5) break
  }

  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = colors.ink
  ctx.font = `900 ${titleSize}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
  const titleLineHeight = titleSize * 1.06
  const titleTop = 250
  titleLines.forEach((line, index) => {
    ctx.fillText(line, 92, titleTop + index * titleLineHeight)
  })
  const titleBottom = titleTop + (titleLines.length - 1) * titleLineHeight

  const statCardTop = 402
  const statCardWidth = 220
  const statCardHeight = 118
  const statLeft = 760
  const stats = [
    ['来源数量', `${sourceCount || 0} 个`],
    ['综合热度', score ? score.toFixed(1) : '--'],
  ]
  stats.forEach(([label, value], index) => {
    const y = statCardTop + index * (statCardHeight + 22)
    ctx.fillStyle = colors.panelStrong
    drawRoundedRect(ctx, statLeft, y, statCardWidth, statCardHeight, 28)
    ctx.fillStyle = colors.subtleText
    ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textBaseline = 'top'
    ctx.fillText(label, statLeft + 28, y + 24)
    ctx.fillStyle = colors.ink
    ctx.font = 'bold 44px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(value, statLeft + 28, y + 56)
  })

  const statBottom = statCardTop + stats.length * statCardHeight + (stats.length - 1) * 22
  const summaryTop = Math.max(720, titleBottom + 92, statBottom + 40)
  const summaryHeight = 308
  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, summaryTop, 924, summaryHeight, 34)

  ctx.fillStyle = colors.accent
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('核心摘要', 110, summaryTop + 52)

  const bullets = splitSummaryIntoBullets(summary, 3)
  let bulletY = summaryTop + 110
  bullets.forEach((bullet) => {
    ctx.fillStyle = colors.accent
    ctx.beginPath()
    ctx.arc(116, bulletY - 10, 7, 0, Math.PI * 2)
    ctx.fill()

    ctx.fillStyle = colors.ink
    ctx.font = '32px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const lines = wrapMixedText(ctx, bullet, 800, 2)
    lines.forEach((line, index) => {
      ctx.fillText(line, 142, bulletY + index * 42)
    })
    bulletY += lines.length * 42 + 34
  })

  const panelTop = summaryTop + summaryHeight + 28
  const leftPanelX = 78
  const rightPanelX = 530
  const panelY = panelTop
  const panelHeight = 250

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, leftPanelX, panelY, 412, panelHeight, 30)
  drawRoundedRect(ctx, rightPanelX, panelY, 472, panelHeight, 30)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('关键词', leftPanelX + 30, panelY + 46)
  ctx.fillText('信号来源', rightPanelX + 30, panelY + 46)

  const tagLabels = normalizeTags(tags, 5)
  let chipX = leftPanelX + 30
  let chipY = panelY + 82
  ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  tagLabels.forEach((label) => {
    const chipWidth = Math.min(ctx.measureText(label).width + 34, 160)
    if (chipX + chipWidth > leftPanelX + 380) {
      chipX = leftPanelX + 30
      chipY += 56
    }
    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, chipX, chipY, chipWidth, 42, 21)
    ctx.fillStyle = '#ffffff'
    ctx.textBaseline = 'middle'
    ctx.fillText(fitTextWithEllipsis(ctx, label, chipWidth - 28), chipX + 17, chipY + 21)
    chipX += chipWidth + 12
  })

  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText(`交叉验证 ${sourceCount || 0} 个来源`, leftPanelX + 30, panelY + 210)

  const sourceLabels = (sources && sources.length > 0 ? sources : ['多源热榜聚合']).slice(0, 4)
  sourceLabels.forEach((source, index) => {
    const rowY = panelY + 86 + index * 38
    ctx.fillStyle = colors.accentSoft
    drawRoundedRect(ctx, rightPanelX + 30, rowY - 22, 32, 32, 16)
    ctx.fillStyle = colors.ink
    ctx.font = 'bold 18px "SF Pro Display", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(String(index + 1), rightPanelX + 46, rowY - 6)

    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'
    ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const sourceText = fitTextWithEllipsis(ctx, source, 350)
    ctx.fillText(sourceText, rightPanelX + 78, rowY)
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('AIINSIGHT / HOT TOPIC CARD', 108, HEIGHT - 86)

  ctx.textAlign = 'right'
  ctx.fillText('Preview Card', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
