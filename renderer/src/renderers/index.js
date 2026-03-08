/**
 * Shared Renderer Module — barrel export.
 * Each renderer is a standalone async function that returns a PNG base64 DataURL.
 * Can be used in Vue components (preview) or in headless browser (renderer service).
 */

export { renderTitleCard, themeColorMap } from './title_card_renderer.js'
export { renderImpactCard } from './impact_card_renderer.js'
export { renderRadarCard } from './radar_card_renderer.js'
export { renderTimelineCard } from './timeline_card_renderer.js'
export { renderTrendCard } from './trend_card_renderer.js'
export { renderDailyRankCard } from './daily_rank_renderer.js'
export { renderHotTopicCard } from './hot_topic_renderer.js'
