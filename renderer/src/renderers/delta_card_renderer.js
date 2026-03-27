/**
 * Delta Card Renderer
 * Shows how the conclusion changed after challenge and revision.
 * Output: 1080×1440 PNG base64 DataURL
 */

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
  formatConfidenceValue,
  wrapMixedText,
} from './editorial_helpers.js'

function drawNarrativeBlock(ctx, {
  x,
  y,
  width,
  height,
  label,
  text,
  colors,
  accent = false,
}) {
  ctx.fillStyle = accent ? colors.panelStrong : colors.panelMuted
  drawRoundedRect(ctx, x, y, width, height, 28)

  if (accent) {
    ctx.fillStyle = colors.accent
    drawRoundedRect(ctx, x, y, 10, height, 5)
  }

  ctx.fillStyle = colors.subtleText
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.font = 'bold 24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText(label, x + 30, y + 44)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 30px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const lines = wrapMixedText(ctx, text, width - 60, 3)
  lines.forEach((line, index) => {
    ctx.fillText(line, x + 30, y + 96 + index * 38)
  })
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {string} payload.opening
 * @param {string} payload.challenge
 * @param {string} payload.revision
 * @param {string} payload.resolution
 * @param {string|number} payload.confidence
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderDeltaCard({
  title = '',
  opening = '',
  challenge = '',
  revision = '',
  resolution = '',
  confidence = '',
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
    section: 'REVISION TRACE',
    title: '判断如何被修正',
    subtitle: confidenceLabel
      ? `修正后结论成熟度：${confidenceLabel}`
      : '把质疑、修正和最后的 stance 摊开讲',
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 390, 924, 846, 34)

  ctx.strokeStyle = colors.accentSoft
  ctx.lineWidth = 6
  ctx.beginPath()
  ctx.moveTo(164, 492)
  ctx.lineTo(164, 1088)
  ctx.stroke()

  ;[
    {
      label: '初版判断',
      text: opening || title || '一开始的直觉判断还不够稳。',
      accent: false,
      y: 446,
      x: 202,
      width: 730,
      height: 184,
    },
    {
      label: '最大质疑',
      text: challenge || '反面证据和缺口指出了原结论里的冒进部分。',
      accent: false,
      y: 678,
      x: 238,
      width: 694,
      height: 214,
    },
    {
      label: '修正结论',
      text: revision || resolution || '最后留下来的判断，必须能同时解释机会和限制。',
      accent: true,
      y: 940,
      x: 202,
      width: 730,
      height: 214,
    },
  ].forEach((block, index) => {
    ctx.fillStyle = index < 2 ? colors.accentSoft : colors.accent
    ctx.beginPath()
    ctx.arc(164, block.y + 48, index < 2 ? 14 : 18, 0, Math.PI * 2)
    ctx.fill()
    drawNarrativeBlock(ctx, { ...block, colors })
  })

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 96, 1254, 888, 48, 24)
  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(
    fitTextWithEllipsis(
      ctx,
      resolution || '真正重要的不是辩了几轮，而是哪一条质疑改变了最终判断。',
      840,
    ),
    122,
    1278,
  )

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('AIINSIGHT / DELTA CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
