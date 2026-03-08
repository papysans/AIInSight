/**
 * Daily Rank Card Renderer
 * Editorial ranking board for AI Daily hot topics.
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
  wrapMixedText,
} from './editorial_helpers.js'

const rankFill = ['#6f2500', '#b45309', '#d97706']
const rankTint = [
  'rgba(255, 239, 214, 0.95)',
  'rgba(255, 244, 225, 0.92)',
  'rgba(255, 248, 233, 0.9)',
]

/**
 * @param {Object} payload
 * @param {string} payload.date
 * @param {string} [payload.title]
 * @param {Array<{rank:number, title:string, score:number, tags?:string[]}>} payload.topics
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderDailyRankCard({ date, title = 'AI 每日热点', topics = [] }) {
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

  drawSoftGlow(ctx, 920, 170, 220, colors.glow)
  drawSoftGlow(ctx, 180, 1220, 220, colors.glow)
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
  ctx.fillText('RANKING BOARD', 304, 112)

  if (date) {
    ctx.textAlign = 'right'
    ctx.fillText(date, WIDTH - 94, 112)
  }

  drawOrbitalMotif(ctx, 860, 200, colors, 0.72)

  ctx.fillStyle = colors.accent
  drawRoundedRect(ctx, 92, 188, 18, 134, 9)
  drawRoundedRect(ctx, 128, 210, 12, 92, 6)

  ctx.fillStyle = colors.ink
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.font = '900 74px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const titleLines = wrapMixedText(ctx, title || 'AI 每日热点', 620, 2)
  titleLines.forEach((line, index) => {
    ctx.fillText(line, 92, 250 + index * 78)
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('多源热榜交叉筛选出的高价值主题', 92, 352)

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 400, 924, 900, 34)

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('RANK', 116, 448)
  ctx.fillText('TOPIC', 212, 448)
  ctx.textAlign = 'right'
  ctx.fillText('SCORE', 956, 448)

  const list = topics.slice(0, 10)
  const rowGap = 12
  const listTop = 476
  const listHeight = 742
  const rowHeight = Math.floor((listHeight - rowGap * Math.max(0, list.length - 1)) / Math.max(1, list.length))
  const showTags = rowHeight >= 92

  list.forEach((topic, index) => {
    const y = listTop + index * (rowHeight + rowGap)
    const rank = topic.rank || index + 1
    const isTop = index < 3
    const fill = isTop ? rankTint[index] : colors.panelMuted

    ctx.fillStyle = fill
    drawRoundedRect(ctx, 96, y, 888, rowHeight, 26)

    if (isTop) {
      ctx.fillStyle = colors.accent
      drawRoundedRect(ctx, 112, y + 14, 8, rowHeight - 28, 4)
    }

    const rankBoxSize = rowHeight >= 88 ? 54 : 46
    ctx.fillStyle = isTop ? rankFill[index] : colors.ink
    drawRoundedRect(ctx, 134, y + (rowHeight - rankBoxSize) / 2, rankBoxSize, rankBoxSize, 18)
    ctx.fillStyle = '#ffffff'
    ctx.font = `bold ${rowHeight >= 88 ? 26 : 22}px "SF Pro Display", sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(String(rank), 134 + rankBoxSize / 2, y + rowHeight / 2)

    const scoreText = topic.score != null ? Number(topic.score).toFixed(1) : '--'
    ctx.fillStyle = isTop ? colors.accentSoft : 'rgba(255,255,255,0.75)'
    drawRoundedRect(ctx, 860, y + (rowHeight - 40) / 2, 92, 40, 20)
    ctx.fillStyle = colors.ink
    ctx.font = 'bold 24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(scoreText, 906, y + rowHeight / 2 + 1)

    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'
    ctx.fillStyle = colors.ink
    const titleX = 220
    const titleWidth = 620

    if (showTags && isTop && topic.tags && topic.tags.length > 0) {
      ctx.font = 'bold 32px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
      const titleText = fitTextWithEllipsis(ctx, topic.title || '未命名话题', titleWidth)
      ctx.fillText(titleText, titleX, y + 40)

      let chipX = titleX
      const chipY = y + 54
      ctx.font = '22px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
      topic.tags.slice(0, 3).forEach((tag) => {
        const label = tag.startsWith('#') ? tag : `#${tag}`
        const width = Math.min(ctx.measureText(label).width + 24, 136)
        ctx.fillStyle = 'rgba(255,255,255,0.75)'
        drawRoundedRect(ctx, chipX, chipY, width, 30, 15)
        ctx.fillStyle = colors.ink
        ctx.textBaseline = 'middle'
        ctx.fillText(fitTextWithEllipsis(ctx, label, width - 18), chipX + 12, chipY + 15)
        chipX += width + 8
      })
    } else {
      ctx.font = `${isTop ? 'bold ' : ''}${rowHeight >= 88 ? 30 : 28}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
      const titleText = fitTextWithEllipsis(ctx, topic.title || '未命名话题', titleWidth)
      ctx.fillText(titleText, titleX, y + rowHeight / 2 + 9)
    }
  })

  ctx.strokeStyle = colors.line
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(112, 1236)
  ctx.lineTo(968, 1236)
  ctx.stroke()

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('评分综合考虑来源覆盖、时效性与 AI 相关度', 112, 1276)

  ctx.textAlign = 'right'
  ctx.fillText(`TOP ${list.length}`, 968, 1276)

  ctx.textAlign = 'left'
  ctx.fillText('AIINSIGHT / RANKING CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('Preview Card', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
