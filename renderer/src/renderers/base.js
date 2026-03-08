const WIDTH = 1080
const HEIGHT = 1440

function createCanvasCard() {
  const canvas = document.createElement('canvas')
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  return { canvas, ctx }
}

function drawBackground(ctx, accent = '#ff7a59') {
  const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT)
  gradient.addColorStop(0, '#0f172a')
  gradient.addColorStop(0.45, '#111827')
  gradient.addColorStop(1, accent)
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, WIDTH, HEIGHT)

  ctx.fillStyle = 'rgba(255,255,255,0.06)'
  ctx.beginPath()
  ctx.arc(860, 220, 220, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(180, 1180, 260, 0, Math.PI * 2)
  ctx.fill()
}

function drawCardShell(ctx, title, subtitle = '') {
  drawBackground(ctx)

  ctx.fillStyle = 'rgba(255,255,255,0.92)'
  roundRect(ctx, 60, 60, WIDTH - 120, HEIGHT - 120, 36)
  ctx.fill()

  ctx.fillStyle = '#0f172a'
  ctx.font = '700 56px "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText(title, 100, 150)

  if (subtitle) {
    ctx.fillStyle = '#475569'
    ctx.font = '400 28px "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(subtitle, 100, 198)
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines = 6) {
  const chars = Array.from(String(text || ''))
  let line = ''
  let lines = 0

  for (const char of chars) {
    const testLine = line + char
    if (ctx.measureText(testLine).width > maxWidth && line) {
      ctx.fillText(line, x, y + lines * lineHeight)
      lines += 1
      line = char
      if (lines >= maxLines) break
    } else {
      line = testLine
    }
  }

  if (lines < maxLines && line) {
    ctx.fillText(line, x, y + lines * lineHeight)
    lines += 1
  }

  return lines
}

function drawTag(ctx, text, x, y, color = '#eef2ff', fg = '#3730a3') {
  ctx.font = '600 24px "PingFang SC", "Noto Sans CJK SC", sans-serif'
  const width = ctx.measureText(text).width + 34
  ctx.fillStyle = color
  roundRect(ctx, x, y - 24, width, 42, 18)
  ctx.fill()
  ctx.fillStyle = fg
  ctx.fillText(text, x + 17, y + 4)
  return width + 12
}

function drawFooter(ctx, text = 'AIInSight') {
  ctx.fillStyle = '#94a3b8'
  ctx.font = '500 22px "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText(text, 100, HEIGHT - 110)
}

function exportPng(canvas) {
  return canvas.toDataURL('image/png')
}

export {
  WIDTH,
  HEIGHT,
  createCanvasCard,
  drawCardShell,
  drawFooter,
  drawTag,
  exportPng,
  roundRect,
  wrapText,
}
