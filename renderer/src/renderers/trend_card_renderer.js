/**
 * Trend Chart Card Renderer
 * Editorial heat-trend card.
 * Output: 1080×1440 PNG base64 DataURL
 */

import { Chart } from 'chart.js/auto'

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
} from './editorial_helpers.js'

const stageConfig = {
  爆发期: { color: '#ef4444', label: '关注度陡升' },
  扩散期: { color: '#ff7a00', label: '讨论面持续扩展' },
  回落期: { color: '#2563eb', label: '热度开始回落' },
}

/**
 * @param {Object} payload
 * @param {string} payload.stage
 * @param {number} payload.growth
 * @param {number[]} payload.curve
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderTrendCard({ stage = '扩散期', growth = 0, curve = [] }) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette
  const stageInfo = stageConfig[stage] || stageConfig['扩散期']

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'TREND SIGNAL',
    title: '热度趋势分析',
    subtitle: stageInfo.label,
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 398, 924, 576, 34)

  const chartCanvas = document.createElement('canvas')
  const chartWidth = 860
  const chartHeight = 470
  chartCanvas.width = chartWidth
  chartCanvas.height = chartHeight
  const chartCtx = chartCanvas.getContext('2d')
  const fill = chartCtx.createLinearGradient(0, 0, 0, chartHeight)
  fill.addColorStop(0, 'rgba(255, 122, 0, 0.22)')
  fill.addColorStop(1, 'rgba(255, 122, 0, 0)')

  const safeCurve = curve.length > 0 ? curve : [18, 24, 32, 48, 61, 58, 66]

  const chartInstance = new Chart(chartCtx, {
    type: 'line',
    data: {
      labels: safeCurve.map((_, index) => `T${index + 1}`),
      datasets: [{
        label: '热度指数',
        data: safeCurve,
        borderColor: stageInfo.color,
        backgroundColor: fill,
        tension: 0.38,
        fill: true,
        pointRadius: 6,
        pointHoverRadius: 7,
        pointBackgroundColor: colors.ink,
        pointBorderColor: '#fff7ed',
        pointBorderWidth: 3,
        borderWidth: 4,
      }],
    },
    options: {
      responsive: false,
      animation: false,
      scales: {
        y: {
          beginAtZero: true,
          suggestedMax: 100,
          ticks: {
            callback: (value) => `${value}%`,
            color: colors.subtleText,
            font: { size: 18, family: 'Noto Sans CJK SC' },
          },
          grid: {
            color: 'rgba(111, 37, 0, 0.12)',
            lineWidth: 1.5,
          },
          border: { display: false },
        },
        x: {
          grid: { display: false },
          ticks: {
            color: colors.ink,
            font: { size: 20, weight: 'bold', family: 'Noto Sans CJK SC' },
          },
          border: { display: false },
        },
      },
      plugins: { legend: { display: false } },
    },
  })

  await new Promise((resolve) => setTimeout(resolve, 80))
  ctx.drawImage(chartCanvas, 110, 442, chartWidth, chartHeight)
  chartInstance.destroy()

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 1000, 300, 224, 30)
  drawRoundedRect(ctx, 390, 1000, 300, 224, 30)
  drawRoundedRect(ctx, 702, 1000, 300, 224, 30)

  const growthText = growth > 0 ? `+${growth}%` : `${growth}%`
  const growthColor = growth >= 100 ? '#ef4444' : growth > 0 ? colors.accent : '#2563eb'
  const peak = safeCurve.length > 0 ? Math.max(...safeCurve).toFixed(0) : '--'

  const stats = [
    ['当前阶段', stage, stageInfo.color],
    ['增长速度', growthText, growthColor],
    ['峰值热度', `${peak}%`, colors.ink],
  ]

  stats.forEach(([label, value, accent], index) => {
    const x = 78 + index * 312
    ctx.fillStyle = colors.subtleText
    ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText(label, x + 28, 1026)

    ctx.fillStyle = accent
    ctx.font = `bold ${index === 1 ? 44 : 40}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    ctx.fillText(value, x + 28, 1082)
  })

  const stages = ['爆发期', '扩散期', '回落期']
  stages.forEach((item, index) => {
    const x = 78 + index * 312 + 28
    const y = 1158
    const itemInfo = stageConfig[item]
    ctx.fillStyle = item === stage ? itemInfo.color : colors.accentSoft
    drawRoundedRect(ctx, x, y, 94, 30, 15)
    ctx.fillStyle = item === stage ? '#ffffff' : colors.ink
    ctx.font = 'bold 18px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(item, x + 47, y + 15)
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.fillText('AIINSIGHT / TREND CARD', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('AIINSIGHT', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
