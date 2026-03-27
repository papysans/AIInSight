/**
 * Evidence Card Renderer
 * Source-backed proof card for topic deep dives.
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

function normalizeEvidenceEntry(item, index) {
  if (typeof item === 'string') {
    return {
      claim: item,
      detail: '',
      source: `证据 ${index + 1}`,
      strength: 'Key',
    }
  }

  return {
    claim: item?.claim || item?.title || item?.summary || item?.event || `证据 ${index + 1}`,
    detail: item?.detail || item?.desc || item?.reason || '',
    source: item?.source || item?.publisher || item?.site || `证据 ${index + 1}`,
    strength: item?.strength || item?.credibility || item?.value || 'Key',
  }
}

/**
 * @param {Object} payload
 * @param {string} payload.title
 * @param {Array<{claim?:string,detail?:string,source?:string,strength?:string}|string>} payload.entries
 * @param {string} payload.takeaway
 * @param {string[]} payload.tags
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderEvidenceCard({
  title = '',
  entries = [],
  takeaway = '',
  tags = [],
}) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  const normalized = (entries || []).slice(0, 3).map(normalizeEvidenceEntry)

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'EVIDENCE BLOCK',
    title: '拿什么证明',
    subtitle: normalized.length > 0 ? `收束成 ${normalized.length} 条关键证据` : '用证据建立这条判断的可信度',
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 388, 924, 822, 34)

  normalized.forEach((item, index) => {
    const boxY = 432 + index * 240

    ctx.fillStyle = index === 0 ? colors.panelMuted : 'rgba(255,255,255,0.44)'
    drawRoundedRect(ctx, 110, boxY, 860, 204, 30)

    ctx.fillStyle = colors.ink
    drawRoundedRect(ctx, 138, boxY + 26, 164, 44, 22)
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 22px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(fitTextWithEllipsis(ctx, item.source, 122), 220, boxY + 48)

    ctx.fillStyle = colors.accent
    drawRoundedRect(ctx, 816, boxY + 26, 126, 40, 20)
    ctx.fillStyle = colors.ink
    ctx.font = 'bold 20px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(fitTextWithEllipsis(ctx, String(item.strength), 90), 879, boxY + 46)

    ctx.fillStyle = colors.ink
    ctx.textAlign = 'left'
    ctx.textBaseline = 'alphabetic'
    ctx.font = 'bold 34px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const claimLines = wrapMixedText(ctx, item.claim, 760, 2)
    claimLines.forEach((line, lineIndex) => {
      ctx.fillText(line, 140, boxY + 118 + lineIndex * 40)
    })

    ctx.fillStyle = colors.subtleText
    ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const detailText = item.detail || '这条证据直接支撑了最终判断的成立条件。'
    const detailLines = wrapMixedText(ctx, detailText, 760, 2)
    detailLines.forEach((line, lineIndex) => {
      ctx.fillText(line, 140, boxY + 174 + lineIndex * 30)
    })
  })

  if (normalized.length === 0) {
    ctx.fillStyle = colors.ink
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.font = 'bold 38px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText('还没有提炼出可展示的关键证据', WIDTH / 2, 682)
  }

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 78, 1234, 924, 66, 24)
  ctx.fillStyle = colors.subtleText
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const summary = takeaway || (normalizeTags(tags, 3).join(' ') || fitTextWithEllipsis(ctx, title || '证据摘要', 720))
  ctx.fillText(fitTextWithEllipsis(ctx, summary, 860), 110, 1267)

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('AIINSIGHT / EVIDENCE CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
