<template>
  <main class="dashboard-shell" :class="{ 'is-loading': loading }">
    <div class="dashboard-grid">
      <div class="left-stack">
        <section class="layout-block block-left-top">
          <TopRolesPanel :stats="viewModel.stats" />
        </section>
        <section class="layout-block block-left-bottom">
          <ScenePanel :plays="viewModel.topPlays" :arc-relations="viewModel.arcRelations" />
        </section>
      </div>

      <section class="layout-block block-main-top">
        <NetworkPanel :graph="viewModel.network" />
      </section>
      <section class="layout-block block-right-top">
        <ThemePanel :data="viewModel.themes" />
      </section>

      <section class="layout-block block-main-bottom">
        <BottomTimelinePanel :data="viewModel.timeline" />
      </section>

      <section class="layout-block block-right-bottom">
        <RightBottomPanel />
      </section>
    </div>

    <div v-if="loading" class="app-mask">
      <div class="loader" />
      <span>正在加载京剧数据</span>
    </div>

    <div v-if="error" class="error-toast">
      {{ error }}
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import BottomTimelinePanel from './components/mainBottom/Panel.vue'
import NetworkPanel from './components/mainTop/Panel.vue'
import ScenePanel from './components/leftBottom/Panel.vue'
import ThemePanel from './components/rightTop/Panel.vue'
import TopRolesPanel from './components/leftTop/Panel.vue'
import RightBottomPanel from './components/rightBottom/Panel.vue'
import { fetchJingjuData } from './services/jingjuApi'

const loading = ref(true)
const error = ref('')
const rawData = ref(null)

const fallbackModel = {
  stats: {
    plays: 0,
    characters: 0,
    avgConfidence: '0.00',
    labeledRate: 0,
    roleDistribution: [],
    roleFeatureRecords: [],
    filterOptions: {
      eras: ['全部时期'],
      roles: ['全部行当'],
      statuses: ['全部角色'],
    },
  },
  network: { nodes: [], links: [] },
  arcRelations: { nodes: [], links: [], playTitle: '' },
  themes: [],
  topPlays: [],
  timeline: [],
}

const viewModel = computed(() => {
  if (!rawData.value) return fallbackModel

  const plays = rawData.value.plays || []
  const characters = rawData.value.characters || plays.flatMap((play) => play.characters || [])
  const cards = rawData.value.meta?.cards || {}

  return {
    stats: buildStats(cards, plays, characters),
    network: buildNetwork(plays, rawData.value),
    arcRelations: buildArcRelations(plays, rawData.value),
    themes: buildThemes(plays, rawData.value),
    topPlays: buildTopPlays(plays),
    timeline: buildTimeline(plays),
  }
})

onMounted(async () => {
  try {
    rawData.value = await fetchJingjuData()
  } catch (err) {
    error.value = `后端数据暂不可用：${err.message}`
  } finally {
    loading.value = false
  }
})

function buildStats(cards, plays, characters) {
  const eraByPlayId = Object.fromEntries(plays.map((play) => [play.play_id, cleanLabel(play.era || '未知时期')]))

  // 左上角图一使用角色级记录，前端可以按时期、行当、标注状态和关键词实时筛选。
  const roleFeatureRecords = characters.map((character) => ({
    id: character.id,
    name: cleanLabel(character.name || '角色'),
    era: eraByPlayId[character.play_id] || cleanLabel(character.era || '未知时期'),
    role: cleanLabel(character.predicted_role || character.major_role || '未定'),
    status: character.is_labeled ? '已标注' : '推断角色',
    feature: cleanLabel(character.identity || character.age_group || character.personality || '未定'),
    confidence: Number(character.confidence || 0),
  }))

  const roleMap = characters.reduce((map, character) => {
    const role = cleanLabel(character.predicted_role || character.major_role || '未定')
    map.set(role, (map.get(role) || 0) + 1)
    return map
  }, new Map())

  const totalCharacters = cards.characters || characters.length
  const labeled = cards.labeled || characters.filter((item) => item.is_labeled).length

  return {
    plays: cards.plays || plays.length,
    characters: totalCharacters,
    avgConfidence: Number(cards.avg_confidence || average(characters, 'confidence')).toFixed(2),
    labeledRate: totalCharacters ? Math.round((labeled / totalCharacters) * 100) : 0,
    roleFeatureRecords,
    filterOptions: {
      eras: ['全部时期', ...uniqueSorted(roleFeatureRecords.map((item) => item.era))],
      roles: ['全部行当', ...uniqueSorted(roleFeatureRecords.map((item) => item.role))],
      statuses: ['全部角色', '已标注', '推断角色'],
    },
    roleDistribution: Array.from(roleMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value]) => ({ name, value })),
  }
}

function buildNetwork(plays, data) {
  const graph = getFirstGraph(plays, data)
  const nodes = (graph.nodes || [])
    .slice(0, 28)
    .map((node, index) => ({
      id: node.id || node.name || `node-${index}`,
      name: cleanLabel(node.name || `角色${index + 1}`),
      symbolSize: Math.max(18, Math.min(56, 16 + Number(node.weighted_degree || node.importance || 1) / 8)),
      category: Number(node.community || index) % 5,
      value: node.weighted_degree || node.importance || 1,
    }))

  const nodeIds = new Set(nodes.map((node) => node.id))
  const links = (graph.edges || graph.links || [])
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .slice(0, 45)
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      value: edge.weight || 1,
      lineStyle: {
        width: Math.max(1, Math.min(6, Number(edge.weight || 1) / 15)),
      },
    }))

  return { nodes, links }
}

function buildArcRelations(plays, data) {
  const graph = getFirstGraph(plays, data)
  const rawNodes = graph.nodes || []
  const rawLinks = graph.edges || graph.links || []

  // 左下角弧线图只保留主要角色，避免半圆关系线过密影响阅读。
  const nodes = rawNodes
    .slice()
    .sort((a, b) => Number(b.weighted_degree || b.importance || 0) - Number(a.weighted_degree || a.importance || 0))
    .slice(0, 14)
    .sort((a, b) => Number(a.community || 0) - Number(b.community || 0))
    .map((node, index) => ({
      id: node.id || node.name || `arc-node-${index}`,
      name: cleanLabel(node.name || `角色${index + 1}`),
      camp: Number(node.community || index % 4),
      value: Number(node.weighted_degree || node.importance || 1),
    }))

  const nodeIds = new Set(nodes.map((node) => node.id))
  const links = rawLinks
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0))
    .slice(0, 26)
    .map((edge) => ({
      source: edge.source,
      target: edge.target,
      weight: Number(edge.weight || 1),
      relation: cleanLabel(edge.relation_type || '互动'),
    }))

  return {
    nodes,
    links,
    playTitle: cleanTitle(rawNodes[0]?.play_title || rawLinks[0]?.play_title || ''),
  }
}

function getFirstGraph(plays, data) {
  return plays.find((play) => play.network?.nodes?.length)?.network || data.network || {}
}

function buildThemes(plays, data) {
  const topics = data.charts?.themes?.topics || plays.flatMap((play) => play.themes?.topics || [])
  const topicMap = topics.reduce((map, item) => {
    const name = cleanLabel(item.topic || item.name || '主题')
    map.set(name, (map.get(name) || 0) + Number(item.score || item.value || 0))
    return map
  }, new Map())

  return Array.from(topicMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({ name, value: Number(value.toFixed(3)) }))
}

function buildTopPlays(plays) {
  return plays
    .map((play) => ({
      id: play.play_id,
      title: cleanTitle(play.title, play.play_id),
      genre: cleanLabel(play.genre || '未分类'),
      era: cleanLabel(play.era || '未知时期'),
      score: Math.round((play.network?.edges?.length || 0) + (play.characters?.length || 0) * 0.35),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 8)
}

function buildTimeline(plays) {
  const eraMap = plays.reduce((map, play) => {
    const name = cleanLabel(play.era || '未知时期')
    const item = map.get(name) || { name, playCount: 0, sceneCount: 0, characterCount: 0 }
    item.playCount += 1
    item.sceneCount += Number(play.scene_count || 0)
    item.characterCount += (play.characters || []).length
    map.set(name, item)
    return map
  }, new Map())

  return Array.from(eraMap.values()).slice(0, 9)
}

function average(records, key) {
  const values = records.map((item) => Number(item[key])).filter(Number.isFinite)
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0
}

function uniqueSorted(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

function cleanLabel(value) {
  const text = String(value || '').replace(/[?]+$/g, '').trim()
  return text && text.length <= 12 ? text : '未定'
}

function cleanTitle(title, id) {
  const text = cleanLabel(title)
  return text === '未定' ? `剧目 ${id || ''}`.trim() : text
}
</script>

<style scoped>
.dashboard-shell {
  position: relative;
  width: 100vw;
  min-height: 100vh;
  padding: 0;
  overflow: hidden;
  background: #877460;
}

.dashboard-grid {
  position: relative;
  display: block;
  width: 100%;
  height: 100vh;
}

.left-stack {
  display: contents;
}

.layout-block {
  position: absolute;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 10px;
  background: #f6f2e7;
}

.block-left-top {
  left: 0.7vw;
  top: 2.86vh;
  width: 25.1vw;
  height: 43.54vh;
}

.block-left-bottom {
  left: 0.7vw;
  top: 47.69vh;
  width: 25.1vw;
  height: 49.79vh;
}

.block-main-top {
  left: 26.52vw;
  top: 2.86vh;
  width: 37.92vw;
  height: 64.27vh;
}

.block-right-top {
  left: 65.03vw;
  top: 2.86vh;
  width: 33.87vw;
  height: 64.27vh;
}

.block-main-bottom {
  left: 26.52vw;
  top: 68.49vh;
  width: 37.92vw;
  height: 28.8vh;
}

.block-right-bottom {
  left: 65.03vw;
  top: 68.49vh;
  width: 33.87vw;
  height: 28.8vh;
}

.app-mask {
  position: fixed;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #3f332b;
  background: rgba(247, 242, 235, 0.78);
  backdrop-filter: blur(6px);
}

.loader {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(139, 29, 29, 0.18);
  border-top-color: #8b1d1d;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

.error-toast {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 11;
  max-width: 420px;
  padding: 12px 14px;
  border: 1px solid rgba(139, 29, 29, 0.2);
  border-radius: 8px;
  color: #7c241f;
  background: #fff8f3;
  box-shadow: 0 12px 28px rgba(54, 42, 32, 0.14);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 980px) {
  .dashboard-shell {
    overflow: auto;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    height: auto;
    padding: 8px;
  }

  .left-stack {
    display: grid;
    grid-column: auto;
    grid-row: auto;
  }

  .layout-block {
    position: static;
    width: auto;
    height: auto;
  }
}
</style>
