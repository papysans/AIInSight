import { renderTitleCard } from './src/renderers/title_card_renderer.js'
import { renderRadarCard } from './src/renderers/radar_card_renderer.js'
import { renderTimelineCard } from './src/renderers/timeline_card_renderer.js'
import { renderTrendCard } from './src/renderers/trend_card_renderer.js'
import { renderDailyRankCard } from './src/renderers/daily_rank_renderer.js'
import { renderHotTopicCard } from './src/renderers/hot_topic_renderer.js'

const renderers = {
  title: renderTitleCard,
  radar: renderRadarCard,
  timeline: renderTimelineCard,
  trend: renderTrendCard,
  daily_rank: renderDailyRankCard,
  hot_topic: renderHotTopicCard,
}

const statusNode = document.getElementById('render-status')

function setStatus(text) {
  if (statusNode) statusNode.textContent = text
}

window.__CARD_RENDERER__ = {
  ready: false,
  listTypes: () => Object.keys(renderers),
  render: async (type, payload) => {
    const fn = renderers[type]
    if (!fn) throw new Error(`Unknown card type: ${type}`)
    setStatus(`rendering ${type}`)
    const result = await fn(payload)
    setStatus('done')
    return result
  },
}

window.__CARD_RENDERER__.ready = true
setStatus('ready')
