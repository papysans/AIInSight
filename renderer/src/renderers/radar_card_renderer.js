/**
 * Radar Chart Card Renderer
 * Editorial platform coverage card.
 * Output: 1080×1440 PNG base64 DataURL
 */

import { Chart } from 'chart.js/auto'

import {
  editorialPalette,
  drawEditorialHeader,
  drawEditorialScaffold,
  drawRoundedRect,
  fitTextWithEllipsis,
} from './editorial_helpers.js'

const radarColors = ['#ff7a00', '#b45309', '#d97706', '#7c3aed', '#2563eb', '#0f766e']

/**
 * @param {Object} payload
 * @param {string[]} payload.labels
 * @param {Object[]} payload.datasets
 * @returns {Promise<string>} PNG base64 DataURL
 */
export async function renderRadarCard({ labels = [], datasets = [] }) {
  const canvas = document.createElement('canvas')
  const WIDTH = 1080
  const HEIGHT = 1440
  canvas.width = WIDTH
  canvas.height = HEIGHT
  const ctx = canvas.getContext('2d')
  const colors = editorialPalette

  drawEditorialScaffold(ctx, WIDTH, HEIGHT, colors)
  const values = Array.isArray(datasets[0]?.data) ? datasets[0].data : []
  const peakIndex = values.length > 0 ? values.indexOf(Math.max(...values)) : -1
  const peakLabel = peakIndex >= 0 ? labels[peakIndex] : '平台'

  const header = drawEditorialHeader(ctx, {
    width: WIDTH,
    section: 'EVIDENCE SIGNAL',
    title: '证据来源分布',
    subtitle: `最高占比来源：${peakLabel}`,
    colors,
    motifScale: 0.74,
    titleWidth: 560,
    titleFont: 72,
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 430, 924, 596, 34)

  const chartCanvas = document.createElement('canvas')
  const chartSize = 620
  chartCanvas.width = chartSize
  chartCanvas.height = chartSize

  const chartInstance = new Chart(chartCanvas.getContext('2d'), {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: 'rgba(255, 122, 0, 0.16)',
        borderColor: colors.accent,
        borderWidth: 4,
        pointBackgroundColor: colors.ink,
        pointBorderColor: '#fff7ed',
        pointBorderWidth: 3,
        pointRadius: 6,
        pointHoverRadius: 7,
      }],
    },
    options: {
      responsive: false,
      animation: false,
      scales: {
        r: {
          beginAtZero: true,
          suggestedMax: 100,
          ticks: {
            stepSize: 20,
            backdropColor: 'transparent',
            color: colors.subtleText,
            font: { size: 18, family: 'Noto Sans CJK SC' },
          },
          grid: {
            color: 'rgba(111, 37, 0, 0.16)',
            lineWidth: 1.5,
          },
          angleLines: {
            color: 'rgba(111, 37, 0, 0.12)',
            lineWidth: 1.5,
          },
          pointLabels: {
            color: colors.ink,
            font: { size: 22, weight: 'bold', family: 'Noto Sans CJK SC' },
          },
        },
      },
      plugins: { legend: { display: false } },
    },
  })

  await new Promise((resolve) => setTimeout(resolve, 80))

  ctx.drawImage(chartCanvas, 100, 460, chartSize, chartSize)
  chartInstance.destroy()

  ctx.fillStyle = colors.panelMuted
  drawRoundedRect(ctx, 734, 470, 236, 168, 28)
  drawRoundedRect(ctx, 734, 658, 236, 168, 28)
  drawRoundedRect(ctx, 734, 846, 236, 148, 28)

  const avg = values.length > 0 ? (values.reduce((acc, value) => acc + value, 0) / values.length).toFixed(1) : '--'
  const maxValue = values.length > 0 ? Math.max(...values).toFixed(0) : '--'

  const statCards = [
    ['峰值平台', peakLabel],
    ['平均覆盖', avg],
    ['最高值', maxValue],
  ]
  statCards.forEach(([label, value], index) => {
    const y = 470 + index * 188
    ctx.fillStyle = colors.subtleText
    ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText(label, 762, y + 22)
    ctx.fillStyle = colors.ink
    ctx.font = `bold ${index === 0 ? 34 : 48}px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif`
    const maxWidth = 180
    const text = index === 0 ? fitTextWithEllipsis(ctx, value, maxWidth) : value
    ctx.fillText(text, 762, y + 70)
  })

  ctx.fillStyle = colors.panelStrong
  drawRoundedRect(ctx, 78, 1054, 924, 254, 32)

  ctx.fillStyle = colors.ink
  ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('来源结构对照', 110, 1100)

  labels.slice(0, 6).forEach((label, index) => {
    const col = index % 2
    const row = Math.floor(index / 2)
    const x = 110 + col * 430
    const y = 1140 + row * 56

    ctx.fillStyle = radarColors[index % radarColors.length]
    drawRoundedRect(ctx, x, y - 24, 28, 28, 14)

    ctx.fillStyle = colors.ink
    ctx.font = '26px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    const name = fitTextWithEllipsis(ctx, label, 210)
    ctx.fillText(name, x + 42, y)

    ctx.textAlign = 'right'
    ctx.font = 'bold 28px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
    ctx.fillText(String(values[index] ?? '--'), x + 360, y)
    ctx.textAlign = 'left'
  })

  ctx.fillStyle = colors.subtleText
  ctx.font = '24px "SF Pro Display", "PingFang SC", "Noto Sans CJK SC", sans-serif'
  ctx.fillText('AIINSIGHT / EVIDENCE RADAR', 108, HEIGHT - 86)
  ctx.textAlign = 'right'
  ctx.fillText('Preview Card', WIDTH - 108, HEIGHT - 86)

  return canvas.toDataURL('image/png')
}
