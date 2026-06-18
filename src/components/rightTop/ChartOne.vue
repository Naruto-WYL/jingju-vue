<template>
  <div class="relation-network">
    <div class="relation-network__toolbar" :class="{ 'relation-network__toolbar--teleported': props.selectTarget }">
      <Teleport v-if="props.selectTarget" :to="props.selectTarget" defer>
        <select
          v-model="selectedScript"
          class="script-select"
          aria-label="选择剧本"
          :disabled="loading || !scriptOptions.length"
          @change="handleScriptSelectChange"
        >
          <option v-for="script in scriptOptions" :key="script" :value="script">
            {{ script }}
          </option>
        </select>
      </Teleport>
      <select
        v-else
        v-model="selectedScript"
        class="script-select"
        aria-label="选择剧本"
        :disabled="loading || !scriptOptions.length"
        @change="handleScriptSelectChange"
      >
        <option v-for="script in scriptOptions" :key="script" :value="script">
          {{ script }}
        </option>
      </select>
    </div>

    <div ref="chartRef" class="relation-network__stage">
  <div class="relation-legend" aria-label="人物关系图例">
    <button
  class="relation-legend__item relation-legend__item--all"
  :class="{ 'is-active': activeRelationType === 'all' }"
  type="button"
  @click="setRelationFilter('all')"
>
      <span class="relation-legend__all-dot"></span>
      <span>全部关系</span>
    </button>

    <button
      v-for="item in relationLegends"
      :key="item.type"
      class="relation-legend__item"
      :class="{ 'is-active': activeRelationType === item.type }"
      type="button"
      @click="setRelationFilter(item.type)"
    >
      <svg class="relation-legend__mark" viewBox="0 0 42 12" aria-hidden="true">
        <path
          d="M4 6 H38"
          :stroke="item.color"
          :stroke-dasharray="item.dash"
          stroke-width="4"
          stroke-linecap="round"
        />
      </svg>
      <span>{{ item.label }}</span>
    </button>
  </div>

  <svg ref="svgRef" class="relation-network__svg" role="img" aria-label="人物关系网络图" />

      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
      <div v-else-if="!currentGraph.nodes.length" class="chart-state">暂无关系数据</div>

      <button
        v-if="isFocusedGraphVisible"
        class="focus-return-btn"
        type="button"
        @click="returnToFullGraph"
      >
        返回全图
      </button>

      <div
        ref="tooltipRef"
        class="relation-tooltip"
        :class="{ 'is-visible': tooltip.visible }"
        :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
      >
        <strong>{{ tooltip.title }}</strong>
        <span v-if="tooltip.sub">{{ tooltip.sub }}</span>
        <p v-if="tooltip.body">{{ tooltip.body }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as d3 from 'd3'
import * as XLSX from 'xlsx'
import {
  findPlayById,
  findPlayByTitle,
  linkageState,
  loadLinkageData,
  selectCharacter,
  standardizeTrade,
} from '../../services/linkageStore'
import coreAvatar from '../../assets/人物图象/核心.png'
import majorAvatar from '../../assets/人物图象/主要.png'
import minorAvatar from '../../assets/人物图象/次要.png'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  selectTarget: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['script-select'])

const DATA_URL = '/数据表合集/2/两剧本人物关系_简化版.csv'
const VIEW_WIDTH = 1600
const VIEW_HEIGHT = 1360
const FOCUS_LAYOUT_DURATION = 2600

const GOLD = '#d4a64a'
const DEEP_GOLD = '#7a4b19'

const EDGE_THEMES = {
  kinship: {
    label: '亲属关系',
    color: '#a65f8f',
    glow: '#ead0e3',
    dash: '',
  },
  romance: {
    label: '婚恋关系',
    color: '#cf6f88',
    glow: '#f2c7d4',
    dash: '5 4',
  },
  power: {
    label: '权力关系',
    color: '#b33a2b',
    glow: '#f1c88a',
    dash: '',
  },
  alliance: {
    label: '同盟关系',
    color: '#2f6f8f',
    glow: '#b9d7e6',
    dash: '',
  },
  conflict: {
    label: '冲突关系',
    color: '#7a2323',
    glow: '#dfa18e',
    dash: '16 7',
  },
  grievance: {
    label: '审判与恩怨',
    color: '#b87924',
    glow: '#efd08a',
    dash: '7 7',
  },
}

const RELATION_TYPES = ['kinship', 'romance', 'power', 'alliance', 'conflict', 'grievance']

const chartRef = ref(null)
const svgRef = ref(null)
const rows = ref([])
const loading = ref(false)
const errorMessage = ref('')
const selectedScript = ref('')
const tooltipRef = ref(null)

const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  title: '',
  sub: '',
  body: '',
})
const activeRelationType = ref('all')

const relationLegends = computed(() => {
  return RELATION_TYPES.map((type) => ({
    type,
    label: EDGE_THEMES[type].label,
    color: EDGE_THEMES[type].color,
    dash: EDGE_THEMES[type].dash,
  }))
})

function setRelationFilter(type) {
  activeRelationType.value = type
  scheduleDraw()
}

function handleScriptSelectChange() {
  if (syncingFromLinkage) return
  emit('script-select', {
    id: currentRows.value[0]?.playId || findPlayByTitle(selectedScript.value)?.play_id || '',
    title: selectedScript.value,
  })
  focusSuppressed.value = true
  previousNodePositions = new Map()
  scheduleDraw()
}

function returnToFullGraph() {
  focusSuppressed.value = true
  previousNodePositions = new Map()
  scheduleDraw()
}

function syncSelectedScriptFromLinkage() {
  const play = findPlayById(linkageState.selectedPlayId)
  const nextScript = play?.title && scriptOptions.value.includes(play.title) ? play.title : scriptOptions.value[0] || ''

  if (!nextScript || selectedScript.value === nextScript) return

  syncingFromLinkage = true
  selectedScript.value = nextScript
  nextTick(() => {
    syncingFromLinkage = false
  })
}
let resizeObserver = null
let drawFrame = 0
let lastStageWidth = 0
let lastStageHeight = 0
let syncingFromLinkage = false
let previousNodePositions = new Map()
const focusSuppressed = ref(false)

const scriptOptions = computed(() => {
  return Array.from(new Set(rows.value.map((row) => row.script).filter(Boolean)))
})

const currentRows = computed(() => {
  if (!selectedScript.value) return []
  return rows.value.filter((row) => row.script === selectedScript.value)
})

const currentGraph = computed(() => buildGraph(currentRows.value))

const isFocusedGraphVisible = computed(() => {
  return Boolean(getFocusCharacterId(currentGraph.value.nodes))
})

onMounted(async () => {
  await loadRows()

  resizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0]
    const width = Math.round(entry?.contentRect.width || 0)
    const height = Math.round(entry?.contentRect.height || 0)

    if (width === lastStageWidth && height === lastStageHeight) return

    lastStageWidth = width
    lastStageHeight = height
    scheduleDraw()
  })

  if (chartRef.value) {
    resizeObserver.observe(chartRef.value)
  }

  await nextTick()
  drawChart()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (drawFrame) cancelAnimationFrame(drawFrame)
  d3.select(svgRef.value).selectAll('*').remove()
})

watch([currentGraph, selectedScript], async () => {
  await nextTick()
  drawChart()
})

watch(
  () => [linkageState.selectedPlayId, linkageState.selectedCharacterId, linkageState.selectedTrade, linkageState.selectedSceneId],
  async () => {
    if (isLinkageTriggerSource()) {
      focusSuppressed.value = false
      syncSelectedScriptFromLinkage()
    }
    await nextTick()
    drawChart()
  },
)

async function loadRows() {
  loading.value = true
  errorMessage.value = ''

  try {
    const linkageData = await loadLinkageData()
    if (linkageData.plays?.length) {
      rows.value = linkageData.plays.flatMap((play) => (play.relations || []).map((relation) => normalizeLinkageRelation(play, relation)))
      syncSelectedScriptFromLinkage()
      return
    }

    const response = await fetch(encodeURI(DATA_URL))
    if (!response.ok) throw new Error(`读取失败：${response.status}`)

    const buffer = await response.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const data = XLSX.utils.sheet_to_json(sheet, { defval: '' })

    rows.value = data.map(normalizeRow).filter((row) => row.script && row.source && row.target)
    selectedScript.value = scriptOptions.value[0] || ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
    rows.value = []
    selectedScript.value = ''
  } finally {
    loading.value = false
  }
}

function normalizeRow(row) {
  return {
    script: text(row['剧本'] ?? row.script ?? row.script_title),
    source: text(row['人物A'] ?? row.source),
    sourceLevel: text(row['A层级'] ?? row.source_level),
    target: text(row['人物B'] ?? row.target),
    targetLevel: text(row['B层级'] ?? row.target_level),
    relation: text(row['四字关系'] ?? row.relation ?? row.relation_type) || '人物关系',
    description: text(row['关系说明'] ?? row.description),
    weight: Math.max(1, Number(row['关系权重'] ?? row.weight ?? 1) || 1),
  }
}

function normalizeLinkageRelation(play, relation) {
  return {
    playId: play.play_id,
    script: play.title,
    source: relation.source_character_id,
    sourceName: relation.source,
    sourceLevel: relation.source_level || inferNodeLevel(play, relation.source_character_id),
    sourceTrade: relation.source_standard_trade || relation.source_trade,
    target: relation.target_character_id,
    targetName: relation.target,
    targetLevel: relation.target_level || inferNodeLevel(play, relation.target_character_id),
    targetTrade: relation.target_standard_trade || relation.target_trade,
    relation: relation.relation_label || relation.relation_type || '同场关系',
    relationType: mapRelationType(relation.relation_type),
    description: relation.relation_desc || relation.evidence || '',
    weight: Math.max(1, Number(relation.weight) || 1),
    sceneIds: relation.scene_ids || [],
  }
}

function inferNodeLevel(play, characterId) {
  const character = play.characters?.find((item) => item.character_id === characterId)
  if (!character) return 'minor'
  const explicitLevel = text(character.role_level || character.roleLevel || character.role_level_label || character.level)
  if (explicitLevel) return normalizeLevel(explicitLevel)
  if (character.importance >= 0.78 || character.role_order <= 2) return 'core'
  if (character.importance >= 0.45 || character.role_order <= 6) return 'major'
  return 'minor'
}

function mapRelationType(type) {
  const value = text(type)
  if (value === 'command' || value === 'power') return 'power'
  if (value === 'support') return 'alliance'
  if (value === 'info') return 'grievance'
  return value || 'alliance'
}

function text(value) {
  return String(value ?? '').trim()
}

function buildGraph(edgeRows) {
  const nodeMap = new Map()
  const links = []
  const playCharacters = getGraphCharacters(edgeRows)

  playCharacters.forEach((character) => {
    upsertNode(
      nodeMap,
      character.character_id,
      character.name,
      character.role_level || inferNodeLevel({ characters: playCharacters }, character.character_id),
      0,
      character.standard_trade || character.trade,
      character.play_id,
      character.importance,
      false,
    )
  })

  edgeRows.forEach((row, index) => {
    upsertNode(nodeMap, row.source, row.sourceName || row.source, row.sourceLevel, row.weight, row.sourceTrade, row.playId)
    upsertNode(nodeMap, row.target, row.targetName || row.target, row.targetLevel, row.weight, row.targetTrade, row.playId)

    links.push({
  id: `edge-${index}`,
  source: row.source,
  target: row.target,
  sourceName: row.sourceName || row.source,
  targetName: row.targetName || row.target,
  sourceTrade: row.sourceTrade || '',
  targetTrade: row.targetTrade || '',
  relation: row.relation,
  relationType: getRelationType(row),
  description: row.description,
  weight: row.weight,
  sceneIds: row.sceneIds || [],
})
  })

  const nodes = Array.from(nodeMap.values()).map((node) => {
    const level = normalizeLevel(node.level)
    const isCore = level === 'core'
    const isMajor = level === 'major'

    return {
      ...node,
      level,
      r: isCore ? 96 : isMajor ? 70 : 58,
      plateWidth: getPlateWidth(node.name, isCore, level),
      core: isCore,
    }
  })

  const hasCore = nodes.some((node) => node.core)
  if (!hasCore) {
    nodes
      .slice()
      .sort((a, b) => b.score - a.score)
      .slice(0, Math.min(2, nodes.length))
      .forEach((node) => {
        node.level = 'core'
        node.core = true
        node.r = 96
        node.plateWidth = getPlateWidth(node.name, true)
      })
  }

  return { nodes, links }
}

function getGraphCharacters(edgeRows) {
  const play = findPlayByTitle(selectedScript.value) || findPlayById(edgeRows[0]?.playId)
  if (!play?.characters?.length) return []

  return play.characters
    .slice()
    .sort((a, b) => {
      return (
        nodeLevelRank(b.role_level) - nodeLevelRank(a.role_level) ||
        Number(b.importance || 0) - Number(a.importance || 0) ||
        Number(a.role_order || 999) - Number(b.role_order || 999)
      )
    })
}

function upsertNode(nodeMap, id, name, level, weight, trade = '', playId = '', importance = 0, countDegree = true) {
  if (!nodeMap.has(id)) {
    nodeMap.set(id, {
      id,
      name,
      trade,
      playId,
      level,
      degree: 0,
      score: Math.max(0, Number(importance) || 0),
      importance: Math.max(0, Number(importance) || 0),
    })
  }

  const node = nodeMap.get(id)
  if (countDegree) node.degree += 1
  node.score += Number(weight) || 0
  node.level = strongerLevel(node.level, level)
  node.importance = Math.max(node.importance || 0, Number(importance) || 0)
  if (trade && !node.trade) node.trade = trade
}

function normalizeLevel(level) {
  const value = text(level)
  if (value === 'core') return 'core'
  if (value === 'major') return 'major'
  if (value === 'minor') return 'minor'
  if (value.includes('核心')) return 'core'
  if (value.includes('主要')) return 'major'
  return 'minor'
}

function nodeLevelRank(level) {
  return {
    core: 3,
    major: 2,
    minor: 1,
  }[normalizeLevel(level)] || 1
}

function strongerLevel(left, right) {
  const rank = {
    core: 3,
    major: 2,
    minor: 1,
  }

  const leftLevel = normalizeLevel(left)
  const rightLevel = normalizeLevel(right)
  return rank[rightLevel] > rank[leftLevel] ? rightLevel : leftLevel
}

function getPlateWidth(name, isCore, level = 'minor') {
  const charCount = Array.from(name).length

  if (isCore || level === 'core') {
    return Math.max(240, Math.min(340, charCount * 48 + 76))
  }

  if (level === 'major') {
    return Math.max(190, Math.min(280, charCount * 40 + 60))
  }

  return Math.max(160, Math.min(230, charCount * 36 + 58))
}

function scheduleDraw() {
  if (drawFrame) cancelAnimationFrame(drawFrame)
  drawFrame = requestAnimationFrame(() => {
    drawFrame = 0
    drawChart()
  })
}

function drawChart() {
  const svgElement = svgRef.value
  if (!svgElement) return

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`)

  if (!currentGraph.value.nodes.length) return

  hideTooltip()

  const graphNodes = currentGraph.value.nodes.map((node, index) => ({
    ...node,
    order: index,
    uid: `node-${index}`,
  }))
  const graphLinks = currentGraph.value.links.map((link, index) => ({
    ...link,
    uid: `edge-${index}`,
  }))

  const requestedFocusId = getFocusCharacterId(graphNodes)
  const renderGraph = buildFocusedGraph(graphNodes, graphLinks, requestedFocusId)
  const nodes = renderGraph.nodes
  const links = renderGraph.links.map((link, index) => ({
    ...link,
    uid: link.uid || `edge-${index}`,
  }))
  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  const isFocusedLayout = Boolean(renderGraph.focusCharacterId)

  if (isFocusedLayout) {
    layoutFocusedGraph(nodes, links, renderGraph.focusCharacterId)
  } else {
    layoutPosterGraph(nodes, links, nodeById)
  }

  const fullLayoutStartPositions = isFocusedLayout ? buildFullLayoutStartPositions(graphNodes, graphLinks) : null
  prepareNodeAnimation(nodes, isFocusedLayout, fullLayoutStartPositions)

  const defs = svg.append('defs')

  
  drawDefs(defs)

  const viewport = svg.append('g')
  svg.call(
    d3
      .zoom()
      .scaleExtent([0.72, 2.4])
      .on('zoom', (event) => {
        viewport.attr('transform', event.transform)
      }),
  )

  const edgeLayer = viewport.append('g')
  const nodeLayer = viewport.append('g')

  drawEdges(edgeLayer, links, nodeById, isFocusedLayout)
  drawNodes(nodeLayer, nodes, links, nodeById, edgeLayer, isFocusedLayout, renderGraph.focusCharacterId)
  applyExternalFocus()
  if (isFocusedLayout) applyFocusedSubgraph(renderGraph.focusCharacterId)
  rememberNodePositions(nodes)
}

function getFocusCharacterId(nodes) {
  const focusId = text(linkageState.selectedCharacterId)
  if (focusSuppressed.value) return ''
  if (!isLinkageTriggerSource() || !focusId) return ''
  return nodes.some((node) => node.id === focusId) ? focusId : ''
}

function buildFocusedGraph(nodes, links, focusCharacterId) {
  if (!focusCharacterId) {
    return {
      nodes,
      links,
      focusCharacterId: '',
    }
  }

  const focusNode = nodes.find((node) => node.id === focusCharacterId)
  if (!focusNode) {
    return {
      nodes,
      links,
      focusCharacterId: '',
    }
  }

  const nodeLookup = new Map(nodes.map((node) => [node.id, node]))
  const directLinks = links.filter((edge) => edge.source === focusCharacterId || edge.target === focusCharacterId)
  const focusLinks = directLinks.slice()

  const hasCoreNeighbor = directLinks.some((edge) => {
    const otherId = edge.source === focusCharacterId ? edge.target : edge.source
    const otherNode = nodeLookup.get(otherId)
    return Boolean(otherNode?.core || normalizeLevel(otherNode?.level) === 'core')
  })

  const fallbackCoreLink =
    !hasCoreNeighbor && normalizeLevel(focusNode.level) !== 'core'
      ? createFallbackCoreLink(nodes, focusNode, focusLinks)
      : null

  if (fallbackCoreLink) focusLinks.push(fallbackCoreLink)

  const visibleIds = new Set([focusCharacterId])
  focusLinks.forEach((edge) => {
    visibleIds.add(edge.source)
    visibleIds.add(edge.target)
  })

  return {
    nodes: nodes
      .filter((node) => visibleIds.has(node.id))
      .map((node) => createFocusedNode(node, focusCharacterId, focusLinks)),
    links: focusLinks,
    focusCharacterId,
  }
}

function createFallbackCoreLink(nodes, focusNode, existingLinks) {
  const targetCore = nodes
    .filter((node) => node.id !== focusNode.id)
    .sort((a, b) => {
      return (
        Number(Boolean(b.core || normalizeLevel(b.level) === 'core')) -
          Number(Boolean(a.core || normalizeLevel(a.level) === 'core')) ||
        nodeLevelRank(b.level) - nodeLevelRank(a.level) ||
        b.score - a.score ||
        b.degree - a.degree ||
        a.order - b.order
      )
    })[0]

  if (!targetCore) return null

  const alreadyLinked = existingLinks.some((edge) => {
    return (
      (edge.source === focusNode.id && edge.target === targetCore.id) ||
      (edge.target === focusNode.id && edge.source === targetCore.id)
    )
  })

  if (alreadyLinked) return null

  return {
    id: `focus-core-${focusNode.id}-${targetCore.id}`,
    source: focusNode.id,
    target: targetCore.id,
    sourceName: focusNode.name,
    targetName: targetCore.name,
    sourceTrade: focusNode.trade || '',
    targetTrade: targetCore.trade || '',
    relation: '\u6838\u5fc3\u5173\u8054',
    relationType: 'alliance',
    description: '\u4eba\u7269\u7f3a\u5c11\u76f4\u63a5\u6838\u5fc3\u8fb9\u65f6\u7684\u8054\u52a8\u8865\u5145',
    weight: 1,
    sceneIds: [],
    syntheticFocus: true,
  }
}

function createFocusedNode(node, focusCharacterId, focusLinks) {
  const isFocusCenter = node.id === focusCharacterId
  const isSyntheticFocusNeighbor = focusLinks.some((edge) => {
    return edge.syntheticFocus && (edge.source === node.id || edge.target === node.id)
  })

  if (isFocusCenter) {
    return {
      ...node,
      isFocusCenter: true,
      isFocusNeighbor: false,
      isSyntheticFocusNeighbor,
    }
  }

  return {
    ...node,
    isFocusCenter: false,
    isFocusNeighbor: true,
    isSyntheticFocusNeighbor,
  }
}

function layoutFocusedGraph(nodes, links, focusCharacterId) {
  const focusNode = nodes.find((node) => node.id === focusCharacterId)
  if (!focusNode) return

  const centerX = VIEW_WIDTH * 0.5
  const centerY = VIEW_HEIGHT * 0.53
  const relatedNodes = nodes
    .filter((node) => node.id !== focusCharacterId)
    .sort((a, b) => {
      return (
        getFocusLinkWeight(b.id, links, focusCharacterId) -
          getFocusLinkWeight(a.id, links, focusCharacterId) ||
        nodeLevelRank(b.level) - nodeLevelRank(a.level) ||
        b.score - a.score ||
        b.degree - a.degree ||
        a.order - b.order
      )
    })

  setPosterNode(focusNode, centerX, centerY, focusNode.r || nodeRadius(focusNode), focusNode.core)
  focusNode.layoutRole = 'focus-center'
  focusNode.anchorX = centerX
  focusNode.anchorY = centerY
  focusNode.clusterId = `focus:${focusCharacterId}`
  focusNode.clusterHubX = centerX
  focusNode.clusterHubY = centerY
  focusNode.fx = centerX
  focusNode.fy = centerY

  const count = relatedNodes.length
  const radiusX = clamp(360 + count * 26, 390, 590)
  const radiusY = clamp(245 + count * 18, 270, 430)

  relatedNodes.forEach((node, index) => {
    const angle = count <= 1 ? -Math.PI / 2 : -Math.PI / 2 + (Math.PI * 2 * index) / count
    const ring = Math.floor(index / 8)
    const wave = count > 5 ? (index % 2) * 34 : 0
    const xRadius = radiusX + ring * 78 + wave
    const yRadius = radiusY + ring * 56 + wave * 0.65

    node.r = nodeRadius(node)
    node.plateWidth = getPlateWidth(node.name, node.core, node.level)
    node.anchorX = centerX + Math.cos(angle) * xRadius
    node.anchorY = centerY + Math.sin(angle) * yRadius
    node.x = node.anchorX
    node.y = node.anchorY
    node.clusterId = `focus:${focusCharacterId}`
    node.clusterHubX = centerX + Math.cos(angle) * 170
    node.clusterHubY = centerY + Math.sin(angle) * 130

    keepNodeInBounds(node)
  })

  runFocusForceLayout(nodes, links, focusNode)
  polishNodeCollisions(nodes, [focusNode])
  nodes.forEach((node) => keepNodeInBounds(node))
  updateEdgeHubs(nodes)
}

function runFocusForceLayout(nodes, links, focusNode) {
  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  const simulationLinks = links
    .map((link) => {
      const source = nodeById.get(link.source)
      const target = nodeById.get(link.target)
      if (!source || !target) return null
      return {
        ...link,
        source,
        target,
      }
    })
    .filter(Boolean)

  focusNode.fx = focusNode.anchorX
  focusNode.fy = focusNode.anchorY

  const simulation = d3
    .forceSimulation(nodes)
    .alpha(1)
    .alphaDecay(0.04)
    .velocityDecay(0.48)
    .force(
      'link',
      d3
        .forceLink(simulationLinks)
        .distance((link) => (link.source.id === focusNode.id || link.target.id === focusNode.id ? 365 : 250))
        .strength((link) => (link.syntheticFocus ? 0.05 : 0.1 + Math.min(0.08, link.weight * 0.012))),
    )
    .force(
      'charge',
      d3.forceManyBody().strength((node) => (node.id === focusNode.id ? -1700 : node.level === 'major' ? -760 : -560)),
    )
    .force(
      'collide',
      d3
        .forceCollide()
        .radius((node) => collisionRadius(node) * 0.8)
        .strength(1)
        .iterations(4),
    )
    .force('x', d3.forceX((node) => node.anchorX ?? focusNode.anchorX).strength((node) => (node.id === focusNode.id ? 1 : 0.34)))
    .force('y', d3.forceY((node) => node.anchorY ?? focusNode.anchorY).strength((node) => (node.id === focusNode.id ? 1 : 0.34)))
    .force('bounds', forcePosterBounds())
    .stop()

  for (let index = 0; index < 240; index += 1) {
    simulation.tick()
  }

  delete focusNode.fx
  delete focusNode.fy
}

function getFocusLinkWeight(nodeId, links, focusCharacterId) {
  return links.reduce((sum, edge) => {
    const connected =
      (edge.source === focusCharacterId && edge.target === nodeId) ||
      (edge.target === focusCharacterId && edge.source === nodeId)
    return connected ? sum + (Number(edge.weight) || 1) : sum
  }, 0)
}

function buildFullLayoutStartPositions(graphNodes, graphLinks) {
  const startNodes = graphNodes.map((node) => ({ ...node }))
  const startLinks = graphLinks.map((link) => ({ ...link }))
  const startNodeById = new Map(startNodes.map((node) => [node.id, node]))

  layoutPosterGraph(startNodes, startLinks, startNodeById)

  return new Map(startNodes.map((node) => [node.id, { x: node.x, y: node.y }]))
}

function prepareNodeAnimation(nodes, shouldAnimate, fullLayoutStartPositions = null) {
  const fallbackX = VIEW_WIDTH * 0.5
  const fallbackY = VIEW_HEIGHT * 0.53

  nodes.forEach((node) => {
    const previous = previousNodePositions.get(node.id) || fullLayoutStartPositions?.get(node.id)
    node.startX = shouldAnimate ? previous?.x ?? fallbackX : node.x
    node.startY = shouldAnimate ? previous?.y ?? fallbackY : node.y
  })
}

function getStartNodeById(nodeById) {
  const startNodeById = new Map()

  nodeById.forEach((node, id) => {
    startNodeById.set(id, {
      ...node,
      x: Number.isFinite(node.startX) ? node.startX : node.x,
      y: Number.isFinite(node.startY) ? node.startY : node.y,
    })
  })

  return startNodeById
}

function rememberNodePositions(nodes) {
  previousNodePositions = new Map(nodes.map((node) => [node.id, { x: node.x, y: node.y }]))
}
function getRelationType(edge) {
  const type = String(edge.relationType || edge.relation || '').trim().toLowerCase()
  const content = `${edge.relation || ''}${edge.description || ''}`

  if (['kinship', 'family'].includes(type)) return 'kinship'
  if (['romance', 'love'].includes(type)) return 'romance'
  if (['command', 'power'].includes(type)) return 'power'
  if (type === 'alliance') return 'alliance'
  if (type === 'support') return 'alliance'
  if (type === 'conflict') return 'conflict'
  if (['info', 'grievance', 'other', 'normal'].includes(type)) return 'grievance'

  if (/夫妻|恋人|婚约|婚姻|姻缘|婚恋|情缘|爱慕/.test(content)) {
    return 'romance'
  }

  if (/父子|母子|父女|母女|兄弟|姐妹|姻亲|亲属|家人|血缘|祖孙|叔侄|亲缘/.test(content)) {
    return 'kinship'
  }

  if (/权力牵制|差遣统属|君臣|主仆|上下|上级|下级|统领|命令|指挥|差遣|率领|调度|主导|掌控|将帅|官民|权力/.test(content)) {
    return 'power'
  }

  if (/同场协作|扶助照应|同盟|合作|协作|盟友|朋友|同僚|结盟|共同|相助|共同作战|共同谋事|师徒|帮助|助力|支援|辅佐|照应|保护|救助|托付|引导|指点|扶助/.test(content)) {
    return 'alliance'
  }

  if (/冲突对峙|对立|冲突|矛盾|敌对|争斗|抗衡|追杀|攻打|反叛|交战/.test(content)) {
    return 'conflict'
  }

  if (/传信谋划|审判|恩怨|报恩|复仇|冤|仇|陷害|欺骗|误会|传递|传信|通报|消息|情报|计策|献计|谋划|密谋|告密|试探|劝说|信息|间接/.test(content)) {
    return 'grievance'
  }

  return 'grievance'
}

function getEdgeTheme(edge) {
  const relationType = getRelationType(edge)
  return EDGE_THEMES[relationType] || EDGE_THEMES.grievance
}

function getEdgeMarkerId(edge) {
  const relationType = getRelationType(edge)

  if (relationType === 'kinship') return 'relationArrowKinship'
  if (relationType === 'romance') return 'relationArrowRomance'
  if (relationType === 'power') return 'relationArrowPower'
  if (relationType === 'alliance') return 'relationArrowAlliance'
  if (relationType === 'conflict') return 'relationArrowConflict'
  return 'relationArrowGrievance'
}
function drawDefs(defs) {
  defs
    .append('filter')
    .attr('id', 'nodeShadow')
    .attr('x', '-25%')
    .attr('y', '-25%')
    .attr('width', '150%')
    .attr('height', '150%')
    .append('feDropShadow')
    .attr('dx', 0)
    .attr('dy', 5)
    .attr('stdDeviation', 4)
    .attr('flood-color', '#3f180f')
    .attr('flood-opacity', 0.24)

createArrowMarker(defs, 'relationArrowKinship', EDGE_THEMES.kinship.color)
createArrowMarker(defs, 'relationArrowRomance', EDGE_THEMES.romance.color)
createArrowMarker(defs, 'relationArrowPower', EDGE_THEMES.power.color)
createArrowMarker(defs, 'relationArrowAlliance', EDGE_THEMES.alliance.color)
createArrowMarker(defs, 'relationArrowConflict', EDGE_THEMES.conflict.color)
createArrowMarker(defs, 'relationArrowGrievance', EDGE_THEMES.grievance.color)

  const gradient = defs
    .append('linearGradient')
    .attr('id', 'plateGold')
    .attr('x1', '0%')
    .attr('y1', '0%')
    .attr('x2', '100%')
    .attr('y2', '100%')

  gradient.append('stop').attr('offset', '0%').attr('stop-color', '#fff2b2')
  gradient.append('stop').attr('offset', '48%').attr('stop-color', GOLD)
  gradient.append('stop').attr('offset', '100%').attr('stop-color', DEEP_GOLD)
}


function createArrowMarker(defs, id, color) {
  defs
    .append('marker')
    .attr('id', id)
    .attr('viewBox', '0 0 12 12')
    .attr('markerWidth', 7)
    .attr('markerHeight', 7)
    .attr('refX', 9.2)
    .attr('refY', 6)
    .attr('orient', 'auto')
    .attr('markerUnits', 'strokeWidth')
    .append('path')
    .attr('d', 'M1.8,2.2 L10,6 L1.8,9.8 Q3.4,6 1.8,2.2 Z')
    .attr('fill', color)
}

function layoutPosterGraph(nodes, links, nodeById) {
  const coreNodes = pickLayoutCoreNodes(nodes)

  placeCoreNodes(coreNodes)
  assignAnchorPositions(nodes, links, coreNodes)
  runAnchorForceLayout(nodes, links, coreNodes, nodeById)
  fitLayoutToPoster(nodes)
  polishNodeCollisions(nodes, coreNodes)
  fitLayoutToPoster(nodes)
  updateEdgeHubs(nodes)
}

function pickLayoutCoreNodes(nodes) {
  const priorityNames = ['周瑜', '诸葛亮', '鲁肃', '曹操', '孙权', '刘备']

  const explicitCoreNodes = nodes
    .filter((node) => node.core)
    .sort((a, b) => {
      const aPriority = priorityNames.includes(a.name) ? priorityNames.indexOf(a.name) : 999
      const bPriority = priorityNames.includes(b.name) ? priorityNames.indexOf(b.name) : 999

      return aPriority - bPriority || b.score - a.score || b.degree - a.degree
    })

  if (explicitCoreNodes.length) return explicitCoreNodes

  const fallbackCoreNodes = nodes
    .slice()
    .sort((a, b) => b.score - a.score || b.degree - a.degree)
    .slice(0, Math.min(3, nodes.length))

  fallbackCoreNodes.forEach((node) => {
    node.core = true
    node.level = 'core'
    node.r = 108
    node.plateWidth = getPlateWidth(node.name, true)
  })

  return fallbackCoreNodes
}

function placeCoreNodes(coreNodes) {
  const positions = getCorePositions(coreNodes.length)

  coreNodes.forEach((node, index) => {
    const position = positions[index] || positions[positions.length - 1]

    setPosterNode(node, position.x, position.y, position.r, true)

    node.layoutRole = position.role
    node.anchorX = position.x
    node.anchorY = position.y
    node.clusterId = `core:${node.id}`
    node.clusterHubX = position.x
    node.clusterHubY = position.y
    node.fx = position.x
    node.fy = position.y
  })
}

function getCorePositions(count) {
  if (count <= 1) {
    return [
      {
        x: VIEW_WIDTH * 0.5,
        y: VIEW_HEIGHT * 0.5,
        r: 118,
        role: 'center',
      },
    ]
  }

  if (count === 2) {
    return [
      {
        x: VIEW_WIDTH * 0.36,
        y: VIEW_HEIGHT * 0.52,
        r: 116,
        role: 'left',
      },
      {
        x: VIEW_WIDTH * 0.64,
        y: VIEW_HEIGHT * 0.52,
        r: 116,
        role: 'right',
      },
    ]
  }

  if (count === 3) {
    return [
      {
        x: VIEW_WIDTH * 0.5,
        y: VIEW_HEIGHT * 0.33,
        r: 112,
        role: 'top',
      },
      {
        x: VIEW_WIDTH * 0.32,
        y: VIEW_HEIGHT * 0.65,
        r: 118,
        role: 'left',
      },
      {
        x: VIEW_WIDTH * 0.69,
        y: VIEW_HEIGHT * 0.65,
        r: 116,
        role: 'right',
      },
    ]
  }

  const centerX = VIEW_WIDTH * 0.5
  const centerY = VIEW_HEIGHT * 0.52
  const radiusX = VIEW_WIDTH * 0.26
  const radiusY = VIEW_HEIGHT * 0.25

  return d3.range(count).map((index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count

    return {
      x: centerX + Math.cos(angle) * radiusX,
      y: centerY + Math.sin(angle) * radiusY,
      r: 108,
      role: Math.cos(angle) < -0.35 ? 'left' : Math.cos(angle) > 0.35 ? 'right' : 'top',
    }
  })
}

function assignAnchorPositions(nodes, links, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))
  const nonCoreNodes = nodes.filter((node) => !coreIds.has(node.id))
  const groups = new Map()

  nonCoreNodes.forEach((node) => {
    const coreLinks = getConnectedCores(node, links, coreNodes)

    node.connectedCores = coreLinks

    const groupKey =
      coreLinks.length >= 2
        ? `bridge:${coreLinks.map((item) => item.core.id).join('|')}`
        : coreLinks.length === 1
          ? `satellite:${coreLinks[0].core.id}`
          : 'fringe'

    node.clusterId = groupKey

    if (!groups.has(groupKey)) groups.set(groupKey, [])
    groups.get(groupKey).push(node)
  })

  groups.forEach((groupNodes, groupKey) => {
    groupNodes.sort((a, b) => b.score - a.score || b.degree - a.degree || a.order - b.order)

    groupNodes.forEach((node, index) => {
      if (groupKey.startsWith('bridge:')) {
        setBridgeAnchor(node, node.connectedCores, index, groupNodes.length)
      } else if (groupKey.startsWith('satellite:')) {
        setSatelliteAnchor(node, node.connectedCores[0].core, index, groupNodes.length)
      } else {
        setFringeAnchor(node, index, groupNodes.length)
      }

      node.x = node.anchorX
      node.y = node.anchorY
      node.r = nodeRadius(node)
      node.plateWidth = getPlateWidth(node.name, node.core, node.level)

      keepNodeInBounds(node)
    })
  })

  nonCoreNodes.forEach((node) => {
    delete node.connectedCores
  })
}

function getConnectedCores(node, links, coreNodes) {
  return coreNodes
    .map((core) => {
      const weight = links.reduce((sum, link) => {
        const connected =
          (link.source === node.id && link.target === core.id) ||
          (link.target === node.id && link.source === core.id)

        return connected ? sum + link.weight : sum
      }, 0)

      return {
        core,
        weight,
      }
    })
    .filter((item) => item.weight > 0)
    .sort((a, b) => b.weight - a.weight)
}

function setSatelliteAnchor(node, core, index, count) {
  const centerX = VIEW_WIDTH * 0.5
  const centerY = VIEW_HEIGHT * 0.52

  const baseAngle = Math.atan2(core.y - centerY, core.x - centerX)
  const span = Math.min(Math.PI * 1.05, Math.PI * (0.42 + count * 0.085))
  const t = count <= 1 ? 0.5 : index / (count - 1)

  const ring = Math.floor(index / 5)
const distance = 450 + ring * 170 + (index % 2) * 64
  const angle = baseAngle - span / 2 + span * t

  node.anchorX = core.x + Math.cos(angle) * distance
  node.anchorY = core.y + Math.sin(angle) * distance

  node.clusterHubX = core.x + Math.cos(baseAngle) * 190
  node.clusterHubY = core.y + Math.sin(baseAngle) * 190
}

function setBridgeAnchor(node, coreLinks, index, count) {
  const totalWeight = d3.sum(coreLinks, (item) => item.weight) || 1

  const baseX = d3.sum(coreLinks, (item) => item.core.x * item.weight) / totalWeight
  const baseY = d3.sum(coreLinks, (item) => item.core.y * item.weight) / totalWeight

  const centerX = VIEW_WIDTH * 0.5
  const centerY = VIEW_HEIGHT * 0.52

  let dx = baseX - centerX
  let dy = baseY - centerY

  const length = Math.hypot(dx, dy) || 1

  dx /= length
  dy /= length

  const tangentX = -dy
  const tangentY = dx

  const offset = (index - (count - 1) / 2) * 270
const outward = 240 + Math.floor(index / 3) * 130

  node.anchorX = baseX + dx * outward + tangentX * offset
  node.anchorY = baseY + dy * outward + tangentY * offset

  node.clusterHubX = baseX + dx * 95
  node.clusterHubY = baseY + dy * 95
}

function setFringeAnchor(node, index, count) {
  const columns = Math.max(3, Math.ceil(Math.sqrt(count)))
  const rows = Math.ceil(count / columns)

  const column = index % columns
  const row = Math.floor(index / columns)

  const left = VIEW_WIDTH * 0.16
  const right = VIEW_WIDTH * 0.84
  const top = VIEW_HEIGHT * 0.77
  const bottom = VIEW_HEIGHT * 0.9

  node.anchorX = columns <= 1 ? VIEW_WIDTH / 2 : left + ((right - left) * column) / (columns - 1)
  node.anchorY = rows <= 1 ? top : top + ((bottom - top) * row) / (rows - 1)

  node.clusterHubX = node.anchorX
  node.clusterHubY = node.anchorY
}

function runAnchorForceLayout(nodes, links, coreNodes, nodeById) {
  const simulationLinks = links
    .map((link) => {
      const source = nodeById.get(link.source)
      const target = nodeById.get(link.target)

      if (!source || !target) return null

      return {
        ...link,
        source,
        target,
      }
    })
    .filter(Boolean)

  const coreIds = new Set(coreNodes.map((node) => node.id))

  coreNodes.forEach((node) => {
    node.fx = node.anchorX
    node.fy = node.anchorY
  })

  const simulation = d3
    .forceSimulation(nodes)
    .alpha(1)
    .alphaDecay(0.028)
    .velocityDecay(0.44)
    .force(
      'link',
      d3
        .forceLink(simulationLinks)
        .distance((link) => {
  if (link.source.core && link.target.core) return 560
  if (link.source.core || link.target.core) return 380 - Math.min(80, link.weight * 10)
  return 340
})
        .strength((link) => {
          if (link.source.core && link.target.core) return 0.18
          if (link.source.core || link.target.core) return 0.085 + link.weight * 0.012
          return 0.05
        }),
    )
    .force(
      'charge',
      d3.forceManyBody().strength((node) => {
        if (node.core) return -1500
        if (node.level === 'major') return -720
        return -520
      }),
    )
    .force(
      'collide',
      d3
        .forceCollide()
        .radius((node) => collisionRadius(node))
        .strength(1)
        .iterations(5),
    )
    .force(
      'x',
      d3
        .forceX((node) => node.anchorX ?? VIEW_WIDTH * 0.5)
        .strength((node) => {
          if (coreIds.has(node.id)) return 0.95
          if (String(node.clusterId || '').startsWith('bridge:')) return 0.22
          return 0.14
        }),
    )
    .force(
      'y',
      d3
        .forceY((node) => node.anchorY ?? VIEW_HEIGHT * 0.52)
        .strength((node) => {
          if (coreIds.has(node.id)) return 0.95
          if (String(node.clusterId || '').startsWith('bridge:')) return 0.22
          return 0.14
        }),
    )
    .force('bounds', forcePosterBounds())
    .stop()

  for (let index = 0; index < 430; index += 1) {
    simulation.tick()
  }

  coreNodes.forEach((node) => {
    delete node.fx
    delete node.fy
  })

  nodes.forEach((node) => {
    keepNodeInBounds(node)
  })
}

function forcePosterBounds() {
  let forceNodes = []

  function force() {
    forceNodes.forEach((node) => {
      const bounds = nodeBounds(node)

      if (bounds.left < 24) node.x += (24 - bounds.left) * 0.18
if (bounds.right > VIEW_WIDTH - 24) node.x -= (bounds.right - (VIEW_WIDTH - 24)) * 0.18
      if (bounds.top < 80) node.y += (80 - bounds.top) * 0.24
      if (bounds.bottom > VIEW_HEIGHT - 80) node.y -= (bounds.bottom - (VIEW_HEIGHT - 80)) * 0.24
    })
  }

  force.initialize = (nodes) => {
    forceNodes = nodes
  }

  return force
}

function collisionRadius(node) {
  if (node.core) return node.r + 130
  if (node.level === 'major') return node.r + 110
  return node.r + 96
}

function fitLayoutToPoster(nodes) {
  const bounds = getLayoutBounds(nodes)

  const target = {
    left: 30,
    right: VIEW_WIDTH - 30,
    top: 115,
    bottom: VIEW_HEIGHT - 120,
  }

  const sourceWidth = Math.max(1, bounds.right - bounds.left)
  const sourceHeight = Math.max(1, bounds.bottom - bounds.top)

  const targetWidth = target.right - target.left
  const targetHeight = target.bottom - target.top

  const scaleX = clamp(targetWidth / sourceWidth, 0.88, 1.6)
  const scaleY = clamp(targetHeight / sourceHeight, 0.88, 1.6)

  const sourceCenterX = (bounds.left + bounds.right) / 2
  const sourceCenterY = (bounds.top + bounds.bottom) / 2

  const targetCenterX = (target.left + target.right) / 2
  const targetCenterY = (target.top + target.bottom) / 2

  nodes.forEach((node) => {
    node.x = targetCenterX + (node.x - sourceCenterX) * scaleX
    node.y = targetCenterY + (node.y - sourceCenterY) * scaleY
    keepNodeInBounds(node)
  })
}

function getLayoutBounds(nodes) {
  return nodes.reduce(
    (result, node) => {
      const bounds = nodeBounds(node)

      return {
        left: Math.min(result.left, bounds.left),
        right: Math.max(result.right, bounds.right),
        top: Math.min(result.top, bounds.top),
        bottom: Math.max(result.bottom, bounds.bottom),
      }
    },
    {
      left: Infinity,
      right: -Infinity,
      top: Infinity,
      bottom: -Infinity,
    },
  )
}

function polishNodeCollisions(nodes, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))

  for (let pass = 0; pass < 120; pass += 1) {
    let moved = false

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const left = nodes[i]
        const right = nodes[j]

        const dx = right.x - left.x
        const dy = right.y - left.y
        const distance = Math.hypot(dx, dy) || 1

        const sameCluster = left.clusterId && left.clusterId === right.clusterId
        const minDistance = collisionRadius(left) + collisionRadius(right) + (sameCluster ? 36 : 72)

        if (distance >= minDistance) continue

        const push = (minDistance - distance) / 2
        const ux = dx / distance
        const uy = dy / distance

        const leftMobility = coreIds.has(left.id) ? 0 : 1
        const rightMobility = coreIds.has(right.id) ? 0 : 1

        left.x -= ux * push * leftMobility
        left.y -= uy * push * leftMobility

        right.x += ux * push * rightMobility
        right.y += uy * push * rightMobility

        keepNodeInBounds(left)
        keepNodeInBounds(right)

        moved = true
      }
    }

    if (!moved) break
  }
}

function updateEdgeHubs(nodes) {
  const groups = d3.group(
    nodes.filter((node) => !node.core),
    (node) => node.clusterId || 'none',
  )

  groups.forEach((groupNodes) => {
    const hubX = d3.mean(groupNodes, (node) => node.x) ?? VIEW_WIDTH / 2
    const hubY = d3.mean(groupNodes, (node) => node.y) ?? VIEW_HEIGHT / 2

    groupNodes.forEach((node) => {
      node.clusterHubX = Number.isFinite(node.clusterHubX) ? (node.clusterHubX + hubX) / 2 : hubX
      node.clusterHubY = Number.isFinite(node.clusterHubY) ? (node.clusterHubY + hubY) / 2 : hubY
    })
  })
}

function nodeBounds(node, x = node.x, y = node.y) {
  const radius = node.r || nodeRadius(node)
  const plateWidth = node.plateWidth || getPlateWidth(node.name, node.core)
  const halfWidth = Math.max(radius + 28, plateWidth / 2 + 34)
  const plaqueBottom = getPlaqueOffset(node) + getPlaqueHeight(node) + 20

  return {
    left: x - halfWidth,
    right: x + halfWidth,
    top: y - radius * 1.35 - 22,
    bottom: y + Math.max(radius * 1.08 + 20, plaqueBottom),
  }
}

function keepNodeInBounds(node) {
  const bounds = nodeBounds(node)

  if (bounds.left < 24) node.x += 24 - bounds.left
  if (bounds.right > VIEW_WIDTH - 24) node.x -= bounds.right - (VIEW_WIDTH - 24)
  if (bounds.top < 24) node.y += 24 - bounds.top
  if (bounds.bottom > VIEW_HEIGHT - 44) node.y -= bounds.bottom - (VIEW_HEIGHT - 44)
}
function getNodeAvatar(node) {
  if (node.level === 'core' || node.core) return coreAvatar
  if (node.level === 'major') return majorAvatar
  return minorAvatar
}
function getNodeTier(node) {
  if (node.core || node.level === 'core') return 'core'
  if (node.level === 'major') return 'major'
  return 'minor'
}
function nodeRadius(node) {
  if (node.core) return node.r || 108
  return node.level === 'minor' ? 62 : 74
}

function getPlaqueHeight(node) {
  if (node.core || node.level === 'core') return 84
  if (node.level === 'major') return 68
  return 56
}
function getPlaqueOffset(node) {
  return node.r * 1.08 - getPlaqueHeight(node) / 2
}

function setPosterNode(node, x, y, radius, isCore = node.core) {
  node.x = x
  node.y = y
  node.r = radius
  node.plateWidth = getPlateWidth(node.name, isCore, node.level)
}

function drawEdges(edgeLayer, links, nodeById, shouldAnimate = false) {
  const startNodeById = shouldAnimate ? getStartNodeById(nodeById) : nodeById
  const edgeGroups = edgeLayer
  .selectAll('g.edge')
  .data(links)
  .join('g')
  .attr('class', 'edge')
  .classed('is-synthetic-focus', (edge) => Boolean(edge.syntheticFocus))
  .classed('is-filter-muted', (edge) => {
    const relationType = getRelationType(edge)
    return activeRelationType.value !== 'all' && relationType !== activeRelationType.value
  })
    .on('mouseenter', (event, edge) => {
      setEdgeActive(edge)
      showEdgeTooltip(event, edge, nodeById)
    })
    .on('mousemove', (event, edge) => {
      setEdgeActive(edge)
      showEdgeTooltip(event, edge, nodeById)
    })
    .on('mouseleave', () => {
      clearActive()
      hideTooltip()
    })

  const backgroundLines = edgeGroups
    .append('path')
    .attr('class', 'edge__line-bg')
    .attr('d', (edge, index) => edgePath(edge, startNodeById, index))
    .attr('stroke', (edge) => getEdgeTheme(edge).glow)
    .attr('stroke-width', (edge) => Math.min(14, 8 + edge.weight * 0.7))

  const mainLines = edgeGroups
    .append('path')
    .attr('id', (edge) => edge.uid)
    .attr('class', 'edge__line')
    .attr('d', (edge, index) => edgePath(edge, startNodeById, index))
    .attr('stroke', (edge) => getEdgeTheme(edge).color)
    .attr('stroke-width', (edge) => Math.min(8, 4.8 + edge.weight * 0.6))
    .attr('stroke-dasharray', (edge) => getEdgeTheme(edge).dash)
    .attr('marker-end', (edge) => `url(#${getEdgeMarkerId(edge)})`)

  const hitLines = edgeGroups
    .append('path')
    .attr('class', 'edge__hit')
    .attr('d', (edge, index) => edgePath(edge, startNodeById, index))

  const labels = edgeGroups
    .append('text')
    .attr('class', 'edge__label')
    .attr('dy', -10)

  labels
    .append('textPath')
    .attr('href', (edge) => `#${edge.uid}`)
    .attr('startOffset', '50%')
    .attr('text-anchor', 'middle')
    .text((edge) => edge.relation)

  if (shouldAnimate) {
    const transition = d3.transition().duration(FOCUS_LAYOUT_DURATION).ease(d3.easeCubicInOut)

    backgroundLines.transition(transition).attr('d', (edge, index) => edgePath(edge, nodeById, index))
    mainLines.transition(transition).attr('d', (edge, index) => edgePath(edge, nodeById, index))
    hitLines.transition(transition).attr('d', (edge, index) => edgePath(edge, nodeById, index))
  }
}

function drawNodes(nodeLayer, nodes, links, nodeById, edgeLayer, shouldAnimate = false, focusCharacterId = '') {
  const filteredNodeIds = new Set()

  if (activeRelationType.value !== 'all') {
    links.forEach((edge) => {
      if (getRelationType(edge) === activeRelationType.value) {
        filteredNodeIds.add(edge.source)
        filteredNodeIds.add(edge.target)
      }
    })
  }
  const nodeGroups = nodeLayer
  .selectAll('g.node')
  .data(nodes)
  .join('g')
  .attr('class', 'node')
  .classed('is-focus-center', (node) => node.id === focusCharacterId)
  .classed('is-focus-neighbor', (node) => shouldAnimate && node.id !== focusCharacterId)
  .classed('is-filter-muted', (node) => {
    return activeRelationType.value !== 'all' && !filteredNodeIds.has(node.id)
  })
  .attr('transform', (node) => {
    const x = shouldAnimate && Number.isFinite(node.startX) ? node.startX : node.x
    const y = shouldAnimate && Number.isFinite(node.startY) ? node.startY : node.y
    return `translate(${x},${y})`
  })
  .style('opacity', shouldAnimate ? 0.72 : null)
  .on('mouseenter', (event, node) => {
    setNodeActive(node.id)
    showNodeTooltip(event, node, links, nodeById)
  })
  .on('mousemove', (event, node) => {
    setNodeActive(node.id)
    showNodeTooltip(event, node, links, nodeById)
  })
  .on('click', (event, node) => {
    event.stopPropagation()
    selectCharacter(node.id, 'rightTopNode')
  })
  .on('mouseleave', () => {
    clearActive()
    hideTooltip()
  })
  .call(
  d3
    .drag()
    .on('start', function (event, node) {
      event.sourceEvent?.stopPropagation()
      hideTooltip()

      d3.select(this)
        .classed('is-dragging', true)
        .raise()
    })
    .on('drag', function (event, node) {
      node.x = event.x
      node.y = event.y

      keepNodeInBounds(node)

      d3.select(this).attr('transform', `translate(${node.x},${node.y})`)

      edgeLayer
        .selectAll('.edge__line-bg')
        .attr('d', (edge, index) => edgePath(edge, nodeById, index))

      edgeLayer
        .selectAll('.edge__line')
        .attr('d', (edge, index) => edgePath(edge, nodeById, index))

      edgeLayer
        .selectAll('.edge__hit')
        .attr('d', (edge, index) => edgePath(edge, nodeById, index))
    })
    .on('end', function () {
      d3.select(this).classed('is-dragging', false)
    }),
)

  if (shouldAnimate) {
    nodeGroups
      .transition()
      .duration(FOCUS_LAYOUT_DURATION)
      .ease(d3.easeCubicInOut)
      .attr('transform', (node) => `translate(${node.x},${node.y})`)
      .style('opacity', 1)
  }

  nodeGroups.append('circle').attr('class', 'node__halo').attr('r', (node) => node.r + 10)
  nodeGroups.append('circle').attr('class', 'node__ring-outer').attr('r', (node) => node.r + 5)
  nodeGroups.append('circle').attr('class', 'node__ring-inner').attr('r', (node) => node.r)

  nodeGroups
  .append('image')
  .attr('class', 'node__avatar')
  .attr('href', (node) => getNodeAvatar(node))
  .attr('xlink:href', (node) => getNodeAvatar(node))
  .attr('x', (node) => -node.r * 1.38)
  .attr('y', (node) => -node.r * 1.55)
  .attr('width', (node) => node.r * 2.76)
  .attr('height', (node) => node.r * 2.76)
  .attr('preserveAspectRatio', 'xMidYMid meet')

  nodeGroups
    .append('circle')
    .attr('class', 'node__avatar-border')
    .attr('r', (node) => node.r *1.18)

  const plaques = nodeGroups
    .append('g')
    .attr('class', 'node__plaque')
    .attr('transform', (node) => `translate(0,${getPlaqueOffset(node)})`)

  plaques
  .append('rect')
  .attr('class', (node) => `node__plaque-bg node__plaque-bg--${getNodeTier(node)}`)
  .attr('x', (node) => -node.plateWidth / 2)
  .attr('y', 0)
  .attr('width', (node) => node.plateWidth)
  .attr('height', (node) => getPlaqueHeight(node))
  .attr('rx', (node) => (node.core ? 18 : 14))
  .attr('ry', (node) => (node.core ? 18 : 14))



  plaques
  .append('text')
  .attr('class', (node) => `node__name node__name--${getNodeTier(node)}`)
  .attr('x', 0)
  .attr('y', (node) => getPlaqueHeight(node) / 2 + 2)
  .attr('text-anchor', 'middle')
  .attr('dominant-baseline', 'middle')
  .text((node) => node.name)

    
}

function edgePath(edge, nodeById, index) {
  const source = nodeById.get(edge.source)
  const target = nodeById.get(edge.target)
  if (!source || !target) return ''

  const control = edgeControlPoint(source, target, index)
  const startToward = control || target
  const endToward = control || source
  const start = pointToward(source, startToward, 20)
  const end = pointToward(target, endToward, 22)

  if (control) {
    return `M ${start.x} ${start.y} Q ${control.x} ${control.y} ${end.x} ${end.y}`
  }

  return `M ${start.x} ${start.y} L ${end.x} ${end.y}`
}

function edgeControlPoint(source, target, index) {
  if (source.core && target.core) {
    return curvedMidPoint(source, target, index, 110)
  }

  const nonCoreNode = source.core && !target.core ? target : target.core && !source.core ? source : null

  if (nonCoreNode) {
    const hubX = Number.isFinite(nonCoreNode.clusterHubX) ? nonCoreNode.clusterHubX : (source.x + target.x) / 2
    const hubY = Number.isFinite(nonCoreNode.clusterHubY) ? nonCoreNode.clusterHubY : (source.y + target.y) / 2

    return {
      x: hubX,
      y: hubY,
    }
  }

  if (source.clusterId && source.clusterId === target.clusterId) {
    return curvedMidPoint(source, target, index, 54)
  }

  return curvedMidPoint(source, target, index, 76)
}

function curvedMidPoint(source, target, index, amount) {
  const midX = (source.x + target.x) / 2
  const midY = (source.y + target.y) / 2
  const dx = target.x - source.x
  const dy = target.y - source.y
  const distance = Math.hypot(dx, dy) || 1
  const nx = -dy / distance
  const ny = dx / distance
  const centerBias = (midX - VIEW_WIDTH / 2) * nx + (midY - VIEW_HEIGHT / 2) * ny
  const side = centerBias > 0 ? 1 : -1
  const lane = (index % 3) - 1
  const offset = side * (amount + lane * 16)

  return {
    x: clamp(midX + nx * offset, 80, VIEW_WIDTH - 80),
    y: clamp(midY + ny * offset, 80, VIEW_HEIGHT - 80),
  }
}

function pointToward(node, target, padding) {
  const dx = target.x - node.x
  const dy = target.y - node.y
  const distance = Math.hypot(dx, dy) || 1

  return {
    x: node.x + (dx / distance) * (node.r + padding),
    y: node.y + (dy / distance) * (node.r + padding),
  }
}



function setNodeActive(nodeId) {
  const connected = new Set([nodeId])

  currentGraph.value.links.forEach((edge) => {
    if (edge.source === nodeId || edge.target === nodeId) {
      connected.add(edge.source)
      connected.add(edge.target)
    }
  })

  const svg = d3.select(svgRef.value)

  svg
    .selectAll('.node')
    .classed('is-muted', (node) => !connected.has(node.id))
    .classed('is-active', (node) => connected.has(node.id))

  svg
    .selectAll('.edge')
    .classed('is-muted', (edge) => edge.source !== nodeId && edge.target !== nodeId)
    .classed('is-active', (edge) => edge.source === nodeId || edge.target === nodeId)
}

function setEdgeActive(activeEdge) {
  const connected = new Set([activeEdge.source, activeEdge.target])
  const svg = d3.select(svgRef.value)

  svg
    .selectAll('.node')
    .classed('is-muted', (node) => !connected.has(node.id))
    .classed('is-active', (node) => connected.has(node.id))

  svg
    .selectAll('.edge')
    .classed('is-muted', (edge) => edge.id !== activeEdge.id)
    .classed('is-active', (edge) => edge.id === activeEdge.id)
}

function clearActive() {
  const svg = d3.select(svgRef.value)
  svg.selectAll('.node,.edge').classed('is-muted', false).classed('is-active', false)
  applyExternalFocus()
  const focusCharacterId = getFocusCharacterId(currentGraph.value.nodes)
  if (focusCharacterId) applyFocusedSubgraph(focusCharacterId)
}

function applyFocusedSubgraph(focusCharacterId) {
  const svg = d3.select(svgRef.value)
  if (!svgRef.value || !focusCharacterId) return

  svg
    .selectAll('.node')
    .classed('is-muted', false)
    .classed('is-active', false)
    .classed('is-focus-center', (node) => node.id === focusCharacterId)
    .classed('is-focus-neighbor', (node) => node.id !== focusCharacterId)

  svg
    .selectAll('.edge')
    .classed('is-muted', false)
    .classed('is-active', false)
}

function applyExternalFocus() {
  const svg = d3.select(svgRef.value)
  if (!svgRef.value || !currentGraph.value.nodes.length) return
  if (focusSuppressed.value) return
  if (!isLinkageTriggerSource()) return

  const focusCharacterId = linkageState.selectedCharacterId
  const focusTrade = text(linkageState.selectedTrade)
  const focusSceneId = linkageState.selectedSceneId
  const shouldUseSceneFocus = linkageState.source !== 'leftTopIcon' && linkageState.source !== 'rightTopNode'
  const activeNodeIds = new Set()
  const activeEdgeIds = new Set()

  currentGraph.value.nodes.forEach((node) => {
    if (focusCharacterId && node.id === focusCharacterId) activeNodeIds.add(node.id)
    if (!focusCharacterId && focusTrade && standardizeTrade(node.trade) === standardizeTrade(focusTrade)) {
      activeNodeIds.add(node.id)
    }
  })

  currentGraph.value.links.forEach((edge) => {
    if (shouldUseSceneFocus && focusSceneId && edge.sceneIds?.includes(focusSceneId)) {
      activeEdgeIds.add(edge.id)
      activeNodeIds.add(edge.source)
      activeNodeIds.add(edge.target)
    }
    if (focusCharacterId && (edge.source === focusCharacterId || edge.target === focusCharacterId)) {
      activeEdgeIds.add(edge.id)
      activeNodeIds.add(edge.source)
      activeNodeIds.add(edge.target)
    } else if (!focusCharacterId && (activeNodeIds.has(edge.source) || activeNodeIds.has(edge.target))) {
      activeEdgeIds.add(edge.id)
    }
  })

  if (!activeNodeIds.size && !activeEdgeIds.size) return

  svg
    .selectAll('.node')
    .classed('is-muted', (node) => !activeNodeIds.has(node.id))
    .classed('is-active', (node) => activeNodeIds.has(node.id))

  svg
    .selectAll('.edge')
    .classed('is-muted', (edge) => !activeEdgeIds.has(edge.id))
    .classed('is-active', (edge) => activeEdgeIds.has(edge.id))
}

function isLinkageTriggerSource() {
  return linkageState.source === 'leftTopIcon' || linkageState.source === 'rightTopNode'
}

function showNodeTooltip(event, node, links, nodeById) {
  const related = links
    .filter((edge) => edge.source === node.id || edge.target === node.id)
    .slice(0, 4)
    .map((edge) => {
      const other = edge.source === node.id ? nodeById.get(edge.target) : nodeById.get(edge.source)
      return `${other?.name || ''}：${edge.relation}`
    })
    .filter(Boolean)

  tooltip.title = node.name
  tooltip.sub = `关系数：${node.degree}  权重：${node.score}`
  tooltip.body = related.join('；')
  moveTooltip(event)
  tooltip.visible = true
}

function showEdgeTooltip(event, edge, nodeById) {
  const source = nodeById.get(edge.source)
  const target = nodeById.get(edge.target)
  const relationType = getRelationType(edge)
  const themeLabel = EDGE_THEMES[relationType]?.label || '审判与恩怨'

  tooltip.title = edge.relation || themeLabel
  tooltip.sub = `${themeLabel}｜${source?.name || edge.source} → ${target?.name || edge.target}`
  tooltip.body = edge.description
  moveTooltip(event)
  tooltip.visible = true
}

function moveTooltip(event) {
  const stage = chartRef.value
  const tooltipElement = tooltipRef.value
  if (!stage || !tooltipElement) return

  const stageRect = stage.getBoundingClientRect()
  const maxX = stage.clientWidth - tooltipElement.offsetWidth - 12
  const maxY = stage.clientHeight - tooltipElement.offsetHeight - 12
  const x = event.clientX - stageRect.left + 14
  const y = event.clientY - stageRect.top + 14

  tooltip.x = clamp(x, 10, Math.max(10, maxX))
  tooltip.y = clamp(y, 10, Math.max(10, maxY))
}

function hideTooltip() {
  tooltip.visible = false
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}
</script>

<style scoped>
/* 关系网络组件的最外层容器 */
.relation-network {
  /* 使用 flex 布局 */
  display: flex;

  /* 子元素上下排列 */
  flex-direction: column;

  /* 工具栏和图表区域之间的间距 */
  gap: 2px;

  /* 宽度占满父容器 */
  width: 100%;

  /* 高度占满父容器 */
  height: 100%;

  /* 最小高度为 0，防止 flex 子元素撑开布局 */
  min-height: 0;

  /* 设置默认文字颜色 */
  color: #273b58;
  background: #FBF6E9;

  /* 设置字体，优先使用楷体，体现戏曲/传统风格 */
  font-family:
    "STKaiti",
    "KaiTi",
    "Microsoft YaHei",
    "PingFang SC",
    sans-serif;
}

/* 顶部工具栏区域 */
.relation-network__toolbar {
  /* 使用 flex 布局 */
  display: flex;

  /* 垂直方向居中 */
  align-items: center;

  /* 内容靠右显示 */
  justify-content: flex-end;

  /* 设置工具栏最小高度 */
  min-height: 32px;
}

.relation-network__toolbar--teleported {
  min-height: 0;
  height: 0;
  overflow: visible;
}

/* 剧本选择下拉框 */
.script-select {
  /* 宽度最大 240px，同时不超过父容器 52% */
  width: min(240px, 52%);

  /* 设置下拉框高度 */
  height: 20px;

  /* 设置内边距，右侧留出下拉箭头空间 */
  padding: 0 32px 0 12px;

  /* 设置边框颜色和透明度 */
  border: 1px solid rgba(142, 47, 36, 0.38);

  /* 设置圆角 */
  border-radius: 6px;

  /* 去掉默认聚焦外轮廓 */
  outline: none;

  /* 设置下拉框背景，使用浅米色渐变 */
  background:
    linear-gradient(180deg, rgba(255, 248, 232, 0.94), rgba(242, 224, 188, 0.94)),
    #f4e8cf;

  /* 设置文字颜色 */
  color: #50301c;

  /* 设置字号 */
  font-size: 16px;

  /* 设置字重 */
  font-weight: 1000;

  /* 鼠标移上去显示可点击手型 */
  cursor: pointer;
}

/* 下拉框获得焦点时的样式 */
.script-select:focus {
  /* 聚焦时加深边框颜色 */
  border-color: rgba(142, 47, 36, 0.74);

  /* 聚焦时添加淡金色外发光 */
  box-shadow: 0 0 0 2px rgba(212, 166, 74, 0.24);
}

.relation-network__stage {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
  background: #FBF6E9;
  background-size: 34px 34px, 34px 34px, auto;

  display: flex;
  flex-direction: column;
  gap: 0px;
}

.focus-return-btn {
  position: absolute;
  top: 62px;
  left: 12px;
  z-index: 6;
  height: 26px;
  padding: 0 12px;
  border: 1px solid rgba(143, 47, 36, 0.46);
  border-radius: 6px;
  background: rgba(255, 249, 237, 0.92);
  color: #7a241d;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  font-size: 12px;
  font-weight: 800;
  line-height: 24px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(80, 35, 12, 0.12);
}

.focus-return-btn:hover {
  border-color: rgba(143, 47, 36, 0.72);
  background: #fff4dc;
}


.relation-legend {
  position: relative;
  z-index: 5;
  width: 100%;
  box-sizing: border-box;

  display: grid;
  grid-template-columns: repeat(4, 104px);
  justify-content: center;
  align-items: center;
  column-gap: 10px;
  row-gap: 4px;

  padding: 0 8px 4px;
  margin-top: -2px;

  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  backdrop-filter: none;
}

.relation-legend__item {
  position: relative;

  display: grid;
  grid-template-columns: 34px 1fr;
  align-items: center;

  width: 104px;
  height: 24px;
  padding: 0;

  border: none;
  border-radius: 0;
  background: transparent;

  color: #5a3518;
  font-family:
    "STKaiti",
    "KaiTi",
    "Microsoft YaHei",
    "PingFang SC",
    sans-serif;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  text-align: left;

  cursor: pointer;
  transition:
    color 0.18s ease,
    transform 0.18s ease;
}

.relation-legend__item.is-active {
  background: transparent;
  box-shadow: none;
  border: none;
  color: #8f2f24;
}


.relation-legend__item--all {
  background: transparent;
  box-shadow: none;
}

.relation-legend__item--all:hover {
  background: transparent;
  box-shadow: none;
  transform: none;
}

.relation-legend__item--all.is-active {
  background: transparent;
  box-shadow: none;
  color: #5a3518;
}
.relation-legend__mark {
  width: 30px;
  height: 12px;
  justify-self: center;
  flex: 0 0 auto;
  overflow: visible;
}

.relation-legend__all-dot {
  width: 10px;
  height: 10px;
  justify-self: center;
  border-radius: 50%;
  background:
    conic-gradient(#a65f8f 0 16.6%, #cf6f88 16.6% 33.2%, #b33a2b 33.2% 49.8%, #2f6f8f 49.8% 66.4%, #7a2323 66.4% 83%, #b87924 83% 100%);
  box-shadow: none;
}

:deep(.edge.is-filter-muted) {
  opacity: 0.08;
}

:deep(.node.is-filter-muted) {
  opacity: 0.2;
}

:deep(.node.is-filter-muted .node__plaque) {
  opacity: 0.55;
}
.relation-network__svg {
  display: block;
  width: 100%;
  flex: 1;
  min-height: 0;
  cursor: grab;
  user-select: none;
}

/* SVG 被鼠标按下时 */
.relation-network__svg:active {
  /* 鼠标变成正在抓取的样式 */
  cursor: grabbing;
}

:deep(.edge__line) {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.78;
  filter: none;
}

:deep(.edge__line-bg) {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.18;
}

/* 关系线鼠标感应区域 */
:deep(.edge__hit) {
  /* 不填充 */
  fill: none;

  /* 透明描边，不可见但可感应鼠标 */
  stroke: transparent;

  /* 感应线宽较大，方便鼠标悬停 */
  stroke-width: 24;

  /* 鼠标事件只在线条描边范围内触发 */
  pointer-events: stroke;

  /* 鼠标移到线上显示手型 */
  cursor: pointer;
}

/* 关系文字标签 */
:deep(.edge__label) {
  /* 文字颜色 */
  fill: #22140d;

  /* 字号较大，方便看清关系名称 */
  font-size: 26px;

  /* 字体加粗 */
  font-weight: 900;

  /* 默认隐藏，悬停时才显示 */
  opacity: 0;

  /* 文字先描边再填充，提高可读性 */
  paint-order: stroke;

  /* 给文字加浅色描边 */
  stroke: rgba(255, 245, 218, 0.95);

  /* 设置文字描边宽度 */
  stroke-width: 6px;

  /* 描边连接处圆润 */
  stroke-linejoin: round;

  /* 禁止文字响应鼠标事件，避免影响线条悬停 */
  pointer-events: none;

  /* 设置透明度变化动画 */
  transition: opacity 0.18s ease;
}

/* 关系边和人物节点的通用过渡 */
:deep(.edge),
:deep(.node) {
  /* 设置透明度和滤镜变化动画 */
  transition:
    opacity 0.2s ease,
    filter 0.2s ease;
}

/* 被弱化的关系边和节点 */
:deep(.edge.is-muted),
:deep(.node.is-muted) {
  /* 降低透明度，突出当前悬停对象 */
  opacity: 0.16;
}

:deep(.edge.is-active .edge__line) {
  opacity: 1;
  filter: drop-shadow(0 0 4px rgba(140, 69, 35, 0.28));
}

:deep(.edge.is-active .edge__line-bg) {
  opacity: 0.34;
}

:deep(.edge.is-synthetic-focus .edge__line) {
  stroke-dasharray: 10 9;
  opacity: 0.64;
}

:deep(.edge.is-synthetic-focus .edge__line-bg) {
  opacity: 0.12;
}

/* 激活状态下显示关系标签 */
:deep(.edge.is-active .edge__label) {
  /* 显示关系文字 */
  opacity: 1;
}

/* 人物节点 */
:deep(.node) {
  /* 鼠标移到节点上显示手型 */
  cursor: pointer;
}

/* 节点外层光环 */
:deep(.node__halo) {
  /* 设置淡金色填充 */
  fill: rgba(255, 238, 184, 0.22);

  /* 设置金色描边 */
  stroke: rgba(212, 166, 74, 0.65);

  /* 设置描边宽度 */
  stroke-width: 4;

  /* 设置虚线效果，让节点更有装饰感 */
  stroke-dasharray: 12 8;
}

:deep(.node__ring-outer) {
  fill: rgba(255, 244, 213, 0.18);
  stroke: url(#plateGold);
  stroke-width: 5;
  filter: url(#nodeShadow);
}

:deep(.node__ring-inner) {
  fill: transparent;
  stroke: transparent;
  stroke-width: 0;
}

/* 节点头像图片 */
:deep(.node__avatar) {
  /* 头像不响应鼠标事件，避免挡住节点交互 */
  pointer-events: none;

  /* 允许头像超出自身盒子显示 */
  overflow: visible;
}

/* 头像圆形边框 */
:deep(.node__avatar-border) {
  /* 不填充，只显示边框 */
  fill: none;

  /* 设置边框颜色 */
  stroke: #6b421b;

  /* 设置边框宽度 */
  stroke-width: 3;
}

/* 人物名牌整体 */
:deep(.node__plaque) {
  /* 给名牌添加投影，增强层次 */
  filter: drop-shadow(0 4px 3px rgba(70, 30, 12, 0.28));
}



:deep(.node__name) {
  font-weight: 900;
  paint-order: stroke;
  stroke-linejoin: round;
  pointer-events: none;
}

:deep(.node__name--core) {
  fill: #ffffff;
  font-size: 60px;
  
  stroke-width: 2.5px;
}

:deep(.node__name--major) {
  fill: #000000;
  font-size: 50px;
  stroke: rgba(24, 64, 70, 0.42);
  stroke-width: 2px;
}

:deep(.node__name--minor) {
  fill: #ffffff;
  font-size: 40px;
  stroke: rgba(255, 255, 255, 0.38);
  stroke-width: 1.8px;
}

/* 节点激活状态 */
:deep(.node.is-active) {
  /* 给激活节点添加金色光晕和阴影 */
  filter:
    drop-shadow(0 0 9px rgba(255, 224, 142, 0.9))
    drop-shadow(0 8px 12px rgba(90, 36, 13, 0.25));
}

/* 图表状态提示，比如加载中、暂无数据 */
.chart-state {
  /* 绝对定位，覆盖整个图表舞台 */
  position: absolute;

  /* 四边都贴合父容器 */
  inset: 0;

  /* 使用 grid 居中内容 */
  display: grid;

  /* 水平和垂直居中 */
  place-items: center;

  /* 设置提示文字颜色 */
  color: #6a4526;

  /* 设置字号 */
  font-size: 14px;

  /* 字体加粗 */
  font-weight: 800;

  /* 不响应鼠标事件，避免遮挡 SVG 交互 */
  pointer-events: none;
}

/* 错误状态提示 */
.chart-state--error {
  /* 错误文字使用红色 */
  color: #9b2b24;
}

/* tooltip 提示框 */
.relation-tooltip {
  /* 绝对定位，位置由 JS 控制 */
  position: absolute;

  /* 设置层级，保证浮在 SVG 上面 */
  z-index: 10;

  /* 设置固定宽度 */
  width: 260px;

  /* 最大宽度不超过容器宽度 */
  max-width: calc(100% - 20px);

  /* 设置内边距 */
  padding: 10px 12px;

  /* 设置边框 */
  border: 1px solid rgba(142, 47, 36, 0.46);

  /* 设置圆角 */
  border-radius: 8px;

  /* 设置半透明浅色背景 */
  background: rgba(255, 249, 232, 0.97);

  /* 设置阴影 */
  box-shadow: 0 10px 24px rgba(50, 24, 10, 0.22);

  /* 设置文字颜色 */
  color: #3a2113;

  /* 默认隐藏 */
  opacity: 0;

  /* tooltip 不响应鼠标事件 */
  pointer-events: none;

  /* 默认略微下移，出现时有动画 */
  transform: translateY(4px);

  /* 设置显示隐藏过渡动画 */
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

/* tooltip 显示状态 */
.relation-tooltip.is-visible {
  /* 显示 tooltip */
  opacity: 1;

  /* 回到原位 */
  transform: translateY(0);
}

/* tooltip 内部标题、副标题、正文 */
.relation-tooltip strong,
.relation-tooltip span,
.relation-tooltip p {
  /* 都作为块级元素显示 */
  display: block;
}

/* tooltip 标题 */
.relation-tooltip strong {
  /* 标题使用京剧红 */
  color: #8f2f24;

  /* 设置标题字号 */
  font-size: 17px;

  /* 设置标题行高 */
  line-height: 1.35;
}

/* tooltip 副标题 */
.relation-tooltip span {
  /* 与标题保持一点距离 */
  margin-top: 3px;

  /* 设置副标题颜色 */
  color: #76502b;

  /* 设置副标题字号 */
  font-size: 12px;

  /* 副标题加粗 */
  font-weight: 800;
}

/* tooltip 正文 */
.relation-tooltip p {
  /* 设置正文外边距 */
  margin: 6px 0 0;

  /* 设置正文颜色 */
  color: #3a2113;

  /* 设置正文字号 */
  font-size: 12px;

  /* 设置正文行高 */
  line-height: 1.55;
}

/* 小屏幕适配 */
@media (max-width: 760px) {
  /* 小屏幕下工具栏 */
  .relation-network__toolbar {
    /* 工具栏内容靠左 */
    justify-content: flex-start;
  }

  /* 小屏幕下剧本选择框 */
  .script-select {
    /* 下拉框宽度占满容器 */
    width: 100%;
  }

  /* 小屏幕下 SVG */
  .relation-network__svg {
    /* 给 SVG 设置最小宽度，避免图表被压得太窄 */
    min-width: 920px;
  }
}
:deep(.node__plaque-bg) {
  stroke: none;
  stroke-width: 0;
}

:deep(.node__plaque-bg--core) {
  fill: #8f2f24;
}

:deep(.node__plaque-bg--major) {
  fill: #869a9c;
}

:deep(.node__plaque-bg--minor) {
  fill: #74775e;
}
:deep(.node.is-dragging) {
  cursor: grabbing;
  filter:
    drop-shadow(0 0 10px rgba(255, 224, 142, 0.95))
    drop-shadow(0 10px 16px rgba(80, 35, 12, 0.28));
}

:deep(.node.is-dragging .node__plaque) {
  filter: drop-shadow(0 6px 5px rgba(70, 30, 12, 0.36));
}
</style>
