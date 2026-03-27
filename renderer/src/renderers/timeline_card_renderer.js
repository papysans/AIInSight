/**
 * Debate Timeline Card Renderer
 * Editorial evolution card for multi-round debate.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
  wrapMixedText,
} from './editorial_helpers.js'

function extractKeyPoint(item) {
  if (item.summary) return item.summary
  const text = item.insight || ''
  const firstSentence = text.match(/^[^。！？.!?]+[。！？.!?]/)
  if (firstSentence) return firstSentence[0]
  return text.substring(0, 48)
}

function computeRowLayout(count) {
  if (count <= 3) return { rowHeight: 182, gap: 18, maxLines: 3 }
  if (count <= 5) return { rowHeight: 152, gap: 14, maxLines: 2 }
  if (count <= 7) return { rowHeight: 128, gap: 12, maxLines: 2 }
  return { rowHeight: 112, gap: 10, maxLines: 2 }
}

/**
 * @param {Object} payload
 * @param {Array<{round:number, title:string, summary:string, insight?:string}>} payload.timeline
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderTimelineCard({ timeline: rawTimeline = [] }) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  const timeline = rawTimeline.slice(0, 8)

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'DEBATE FLOW',
    title: '辩论演化过程',
    subtitle: `展示 ${timeline.length} 轮关键转折`,
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 392, 924, 892, 34)

  const { rowHeight, gap, maxLines } = computeRowLayout(Math.max(1, timeline.length))
  const lineX = 154
  const rowTop = 442
  const totalHeight = timeline.length * rowHeight + Math.max(0, timeline.length - 1) * gap
  const offset = Math.max(0, (796 - totalHeight) / 2)

  if (timeline.length > 1) {
    ctx.strokeStyle = colors.accentSoft
    ctx.lineWidth = 6
    ctx.beginPath()
    ctx.moveTo(lineX, rowTop + offset + 40)
    ctx.lineTo(lineX, rowTop + offset + totalHeight - 40)
    ctx.stroke()
  }

  timeline.forEach((item, index) => {
    const y = rowTop + offset + index * (rowHeight + gap)
    const isLast = index === timeline.length - 1

    ctx.fillStyle = index < 2 ? colors.panelMuted : 'rgba(255,255,255,0.42)'
    drawRoundedRect(ctx, 212, y, 742, rowHeight, 28)

    if (isLast) {
      ctx.fillStyle = colors.accent
      drawRoundedRect(ctx, 212, y, 10, rowHeight, 5)
    }

    ctx.fillStyle = index < 2 ? colors.accent : colors.ink
    drawRoundedRect(ctx, 118, y + (rowHeight - 72) / 2, 72, 72, 24)

    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`R${item.round || index + 1}`, 154, y + rowHeight / 2)

    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'
    ctx.fillStyle = colors.ink
    ctx.font = `bold ${rowHeight >= 150 ? 32 : 28}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    const titleText = fitTextWithEllipsis(ctx, item.title || `第 ${index + 1} 轮`, 600)
    ctx.fillText(titleText, 246, y + 40)

    const keyPoint = extractKeyPoint(item)
    ctx.fillStyle = colors.subtleText
    ctx.font = `${rowHeight >= 150 ? 24 : 22}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    const lines = wrapMixedText(ctx, keyPoint, 610, maxLines)
    lines.forEach((line, lineIndex) => {
      ctx.fillText(line, 246, y + 82 + lineIndex * 34)
    })

    if (isLast) {
      ctx.fillStyle = colors.accentSoft
      drawRoundedRect(ctx, 814, y + rowHeight - 50, 112, 28, 14)
      ctx.fillStyle = colors.ink
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.font = 'bold 18px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
      ctx.fillText('当前结论', 870, y + rowHeight - 36)
    }
  })

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 96, 1224, 888, 60, 24)
  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  const summaryText = rawTimeline.length > timeline.length
    ? `展示前 ${timeline.length} 轮关键节点，共 ${rawTimeline.length} 轮`
    : `共 ${timeline.length} 轮讨论，结论随回合逐步收敛`
  ctx.fillText(summaryText, 124, 1254)

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('AIINSIGHT / DEBATE TIMELINE', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
