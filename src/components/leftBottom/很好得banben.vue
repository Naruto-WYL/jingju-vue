<template>
  <div class="relation-network">
    <div class="relation-network__toolbar" :class="{ 'relation-network__toolbar--teleported': props.selectTarget }">
      <Teleport v-if="props.selectTarget" :to="props.selectTarget" defer>
        <select
          v-model="selectedScript"
          class="script-select"
          aria-label="选择剧本"
          :disabled="loading || !scriptOptions.length"
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
      >
        <option v-for="script in scriptOptions" :key="script" :value="script">
          {{ script }}
        </option>
      </select>
    </div>

    <div ref="chartRef" class="relation-network__stage">
      <svg ref="svgRef" class="relation-network__svg" role="img" aria-label="人物关系网络图" />

      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
      <div v-else-if="!currentGraph.nodes.length" class="chart-state">暂无关系数据</div>

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
import shengAvatar from '../../assets/step1/生.png'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps({
  selectTarget: {
    type: String,
    default: '',
  },
})

const DATA_URL = '/数据表合集/2/new.xlsx'
const VIEW_WIDTH = 1600
const VIEW_HEIGHT = 1360
const EDGE_COLOR = '#8f2f24'
const PLAQUE_COLOR = '#8f2f24'
const GOLD = '#d4a64a'
const DEEP_GOLD = '#7a4b19'

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

let resizeObserver = null
let drawFrame = 0
let lastStageWidth = 0
let lastStageHeight = 0

const scriptOptions = computed(() => {
  return Array.from(new Set(rows.value.map((row) => row.script).filter(Boolean)))
})

const currentRows = computed(() => {
  if (!selectedScript.value) return []
  return rows.value.filter((row) => row.script === selectedScript.value)
})

const currentGraph = computed(() => buildGraph(currentRows.value))

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

async function loadRows() {
  loading.value = true
  errorMessage.value = ''

  try {
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

function text(value) {
  return String(value ?? '').trim()
}

function buildGraph(edgeRows) {
  const nodeMap = new Map()
  const links = []

  edgeRows.forEach((row, index) => {
    upsertNode(nodeMap, row.source, row.sourceLevel, row.weight)
    upsertNode(nodeMap, row.target, row.targetLevel, row.weight)

    links.push({
      id: `edge-${index}`,
      source: row.source,
      target: row.target,
      relation: row.relation,
      description: row.description,
      weight: row.weight,
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
      plateWidth: getPlateWidth(node.name, isCore),
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

function upsertNode(nodeMap, name, level, weight) {
  if (!nodeMap.has(name)) {
    nodeMap.set(name, {
      id: name,
      name,
      level,
      degree: 0,
      score: 0,
    })
  }

  const node = nodeMap.get(name)
  node.degree += 1
  node.score += weight
  node.level = strongerLevel(node.level, level)
}

function normalizeLevel(level) {
  const value = text(level)
  if (value.includes('核心')) return 'core'
  if (value.includes('主要')) return 'major'
  return 'minor'
}

function strongerLevel(left, right) {
  const rank = {
    core: 3,
    major: 2,
    minor: 1,
  }

  return rank[normalizeLevel(right)] > rank[normalizeLevel(left)] ? right : left
}

function getPlateWidth(name, isCore) {
  const charCount = Array.from(name).length
  return Math.max(isCore ? 160 : 112, Math.min(isCore ? 220 : 170, charCount * (isCore ? 34 : 26) + 42))
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

  const nodes = currentGraph.value.nodes.map((node, index) => ({
    ...node,
    order: index,
    uid: `node-${index}`,
  }))
  const links = currentGraph.value.links.map((link, index) => ({
    ...link,
    uid: `edge-${index}`,
  }))

  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  layoutPosterGraph(nodes, links)

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

  drawEdges(edgeLayer, links, nodeById)
  drawNodes(nodeLayer, nodes, links, nodeById)
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

  defs
    .append('marker')
    .attr('id', 'relationArrow')
    .attr('viewBox', '0 0 12 12')
    .attr('markerWidth', 5.8)
    .attr('markerHeight', 5.8)
    .attr('refX', 9)
    .attr('refY', 6)
    .attr('orient', 'auto-start-reverse')
    .attr('markerUnits', 'strokeWidth')
    .append('path')
    .attr('d', 'M1.5,2 L10,6 L1.5,10 Z')
    .attr('fill', EDGE_COLOR)
}

function layoutPosterGraph(nodes, links) {
  const coreNodes = pickCoreNodes(nodes)
  const corePositions = getCorePositions(coreNodes.length)

  coreNodes.forEach((node, index) => {
    const point = corePositions[index] || corePositions[corePositions.length - 1]
    setPosterNode(node, point.x, point.y, point.role === 'top' && coreNodes.length > 2 ? 92 : 108, true)
    node.layoutRole = point.role
  })

  const clusters = buildRelationClusters(nodes, links, coreNodes)
  assignClusterLanes(clusters)
  placeClusters(clusters, coreNodes)
  relaxLayout(nodes, coreNodes)
  expandLayoutToCanvas(nodes)
  spreadLayoutEvenly(nodes, coreNodes)
  relaxLayout(nodes, coreNodes)
  updateClusterHubs(clusters)
}

function pickCoreNodes(nodes) {
  const explicit = nodes.filter((node) => node.core)
  if (explicit.length) return explicit

  const fallback = nodes
    .slice()
    .sort((a, b) => b.score - a.score || b.degree - a.degree)
    .slice(0, Math.min(3, nodes.length))

  fallback.forEach((node) => {
    node.core = true
    node.level = 'core'
  })

  return fallback
}

function buildRelationClusters(nodes, links, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))
  const nonCoreNodes = nodes.filter((node) => !coreIds.has(node.id))
  const nonCoreIds = new Set(nonCoreNodes.map((node) => node.id))
  const unionFind = createUnionFind(nonCoreNodes.map((node) => node.id))

  links.forEach((link) => {
    if (nonCoreIds.has(link.source) && nonCoreIds.has(link.target)) {
      unionFind.union(link.source, link.target)
    }
  })

  const peerComponents = new Map()
  nonCoreNodes.forEach((node) => {
    const root = unionFind.find(node.id)
    if (!peerComponents.has(root)) peerComponents.set(root, [])
    peerComponents.get(root).push(node)
  })

  const coreSignatureById = new Map()
  nonCoreNodes.forEach((node) => {
    coreSignatureById.set(node.id, getCoreLinks(node, links, coreNodes).map((item) => item.core.id).sort().join('__'))
  })

  const singleCoreBuckets = new Map()
  const multiCoreBuckets = new Map()
  const clusters = []

  Array.from(peerComponents.values()).forEach((componentNodes) => {
    const info = summarizeCluster(componentNodes, links, coreNodes)
    const sameSingleCore = info.coreIds.length === 1 && !hasCrossCoreSignaturePeer(componentNodes, links, nonCoreIds, coreSignatureById)

    if (sameSingleCore) {
      const key = info.coreIds[0]
      if (!singleCoreBuckets.has(key)) singleCoreBuckets.set(key, [])
      singleCoreBuckets.get(key).push(...componentNodes)
      return
    }

    if (componentNodes.length === 1 && info.coreIds.length > 1) {
      const key = getCoreRelationSignature(componentNodes[0], links, coreNodes)
      if (!multiCoreBuckets.has(key)) multiCoreBuckets.set(key, [])
      multiCoreBuckets.get(key).push(componentNodes[0])
      return
    }

    clusters.push(makeCluster(componentNodes, links, coreNodes))
  })

  singleCoreBuckets.forEach((bucketNodes) => {
    splitClusterNodes(bucketNodes, 6).forEach((group) => {
      clusters.push(makeCluster(group, links, coreNodes))
    })
  })

  multiCoreBuckets.forEach((bucketNodes) => {
    if (bucketNodes.length > 1) {
      clusters.push(makeCluster(bucketNodes, links, coreNodes))
      return
    }

    clusters.push(makeCluster(bucketNodes, links, coreNodes))
  })

  return clusters
    .map((cluster, index) => ({ ...cluster, id: `cluster-${index}` }))
    .sort((a, b) => clusterTypeRank(a.type) - clusterTypeRank(b.type) || b.weight - a.weight || b.nodes.length - a.nodes.length)
}

function createUnionFind(ids) {
  const parent = new Map(ids.map((id) => [id, id]))

  function find(id) {
    const current = parent.get(id)
    if (current === id) return id

    const root = find(current)
    parent.set(id, root)
    return root
  }

  function union(left, right) {
    if (!parent.has(left) || !parent.has(right)) return

    const rootLeft = find(left)
    const rootRight = find(right)
    if (rootLeft !== rootRight) parent.set(rootRight, rootLeft)
  }

  return { find, union }
}

function makeCluster(clusterNodes, links, coreNodes) {
  const info = summarizeCluster(clusterNodes, links, coreNodes)

  return {
    id: '',
    nodes: clusterNodes.slice().sort((a, b) => b.score - a.score || a.order - b.order),
    cores: info.cores,
    coreIds: info.coreIds,
    type: info.type,
    weight: info.weight,
  }
}

function summarizeCluster(clusterNodes, links, coreNodes) {
  const coreWeights = new Map(coreNodes.map((core) => [core.id, 0]))

  clusterNodes.forEach((node) => {
    getCoreLinks(node, links, coreNodes).forEach((item) => {
      coreWeights.set(item.core.id, (coreWeights.get(item.core.id) || 0) + item.weight)
    })
  })

  const coreEntries = Array.from(coreWeights.entries())
    .filter(([, weight]) => weight > 0)
    .sort((a, b) => b[1] - a[1])

  let cores = coreEntries
    .map(([id]) => coreNodes.find((core) => core.id === id))
    .filter(Boolean)
  let coreIds = cores.map((core) => core.id)
  let type = 'fringe'

  if (coreIds.length === 1) {
    type = 'satellite'
  } else if (coreIds.length > 1) {
    const firstWeight = coreEntries[0]?.[1] || 0
    const secondWeight = coreEntries[1]?.[1] || 0

    if (hasInternalLinks(clusterNodes, links) && firstWeight >= secondWeight * 1.45) {
      cores = cores.slice(0, 1)
      coreIds = coreIds.slice(0, 1)
      type = 'satellite'
    } else {
      type = 'bridge'
    }
  }

  return {
    cores,
    coreIds,
    type,
    weight: clusterNodes.reduce((sum, node) => sum + node.score, 0),
  }
}

function splitClusterNodes(nodes, maxSize) {
  const ordered = nodes.slice().sort((a, b) => b.score - a.score || a.order - b.order)
  const groups = []

  for (let index = 0; index < ordered.length; index += maxSize) {
    groups.push(ordered.slice(index, index + maxSize))
  }

  return groups
}

function assignClusterLanes(clusters) {
  const counts = new Map()

  clusters.forEach((cluster) => {
    const key = `${cluster.type}:${cluster.coreIds.slice().sort().join('__') || 'fringe'}`
    const lane = counts.get(key) || 0
    counts.set(key, lane + 1)
    cluster.lane = lane
  })
}

function placeClusters(clusters, coreNodes) {
  const placedRects = coreNodes.map((node) => nodeBounds(node))

  clusters.forEach((cluster) => {
    const candidates = getClusterCandidates(cluster)
    const placement = chooseClusterPlacement(cluster, candidates, placedRects)

    applyClusterPlacement(cluster, placement)
    cluster.nodes.forEach((node) => placedRects.push(nodeBounds(node)))
  })
}

function getClusterCandidates(cluster) {
  if (cluster.type === 'bridge') return getBridgeCandidates(cluster)
  if (cluster.type === 'satellite') return getSatelliteCandidates(cluster)
  return getFringeCandidates(cluster)
}

function getSatelliteCandidates(cluster) {
  const core = cluster.cores[0]
  if (!core) return getFringeCandidates(cluster)

  const angles = rotateValues(getSatelliteAngles(core), cluster.lane || 0)
  const distances = [440, 580, 720, 850]
  const candidates = []

  distances.forEach((distance, ringIndex) => {
    angles.forEach((angle, angleIndex) => {
      const point = polarPoint(core.x, core.y, distance, angle)
      candidates.push({
        x: point.x,
        y: point.y,
        mode: getPackMode(cluster),
        priority: ringIndex * 14 + angleIndex,
      })
    })
  })

  return candidates
}

function getSatelliteAngles(core) {
  if (core.layoutRole === 'left') return [180, 135, 225, 90, 270, 45, 315]
  if (core.layoutRole === 'right') return [0, 45, -45, 90, -90, 135, -135]
  if (core.layoutRole === 'top') return [90, 135, 45, 180, 0, 225, -45]
  return [-90, 90, 180, 0, 45, 135, -45, -135]
}

function getBridgeCandidates(cluster) {
  const [coreA, coreB] = cluster.cores
  if (!coreA || !coreB) return getFringeCandidates(cluster)

  const midX = (coreA.x + coreB.x) / 2
  const midY = (coreA.y + coreB.y) / 2
  const dx = coreB.x - coreA.x
  const dy = coreB.y - coreA.y
  const distance = Math.hypot(dx, dy) || 1
  const horizontalPair = Math.abs(dy) < 150
  const axisX = dx / distance
  const axisY = dy / distance
  let normalX = -axisY
  let normalY = axisX

  if ((midX - VIEW_WIDTH / 2) * normalX + (midY - VIEW_HEIGHT / 2) * normalY < 0) {
    normalX *= -1
    normalY *= -1
  }

  const preferredSide = horizontalPair && (cluster.lane || 0) % 2 === 1 ? -1 : 1
  const sides = horizontalPair ? [preferredSide, -preferredSide] : [1]
  const radialOffsets = [270, 400, 540, 160]
  const alongOffsets = [0, 220, -220, 380, -380]
  const candidates = []

  radialOffsets.forEach((radial, radialIndex) => {
    sides.forEach((side, sideIndex) => {
      alongOffsets.forEach((along, alongIndex) => {
        candidates.push({
          x: midX + normalX * radial * side + axisX * along,
          y: midY + normalY * radial * side + axisY * along,
          mode: getPackMode(cluster),
          priority: radialIndex * 24 + sideIndex * 10 + alongIndex,
        })
      })
    })
  })

  return candidates
}

function getFringeCandidates(cluster) {
  const columns = Math.max(3, Math.ceil(Math.sqrt(cluster.nodes.length + 2)))
  return d3.range(columns * 3).map((index) => ({
    x: spreadValue(index % columns, columns, 260, VIEW_WIDTH - 260),
    y: VIEW_HEIGHT - 120 - Math.floor(index / columns) * 230,
    mode: getPackMode(cluster),
    priority: index,
  }))
}

function chooseClusterPlacement(cluster, candidates, placedRects) {
  return candidates.reduce((best, candidate) => {
    const placement = packCluster(cluster, candidate)
    const score = scorePlacement(placement, placedRects, candidate.priority)
    return !best || score < best.score ? { ...placement, score } : best
  }, null)
}

function packCluster(cluster, candidate) {
  const nodes = cluster.nodes
  const gapX = 282
  const gapY = 268
  const positions = []

  if (candidate.mode === 'row') {
    nodes.forEach((node, index) => {
      positions.push({ node, x: candidate.x + (index - (nodes.length - 1) / 2) * gapX, y: candidate.y })
    })
  } else if (candidate.mode === 'column') {
    nodes.forEach((node, index) => {
      positions.push({ node, x: candidate.x, y: candidate.y + (index - (nodes.length - 1) / 2) * gapY })
    })
  } else {
    const columns = getGridColumns(cluster)
    const rows = Math.ceil(nodes.length / columns)

    nodes.forEach((node, index) => {
      const row = Math.floor(index / columns)
      const column = index % columns
      positions.push({
        node,
        x: candidate.x + (column - (columns - 1) / 2) * gapX,
        y: candidate.y + (row - (rows - 1) / 2) * gapY,
      })
    })
  }

  return shiftPlacementInsideBounds({ positions, candidate })
}

function shiftPlacementInsideBounds(placement) {
  const bounds = placementBounds(placement.positions)
  let dx = 0
  let dy = 0

  if (bounds.left < 82) dx = 82 - bounds.left
  if (bounds.right > VIEW_WIDTH - 82) dx = VIEW_WIDTH - 82 - bounds.right
  if (bounds.top < 24) dy = 24 - bounds.top
  if (bounds.bottom > VIEW_HEIGHT - 44) dy = VIEW_HEIGHT - 44 - bounds.bottom

  if (!dx && !dy) return placement

  return {
    ...placement,
    positions: placement.positions.map((position) => ({
      ...position,
      x: position.x + dx,
      y: position.y + dy,
    })),
  }
}

function scorePlacement(placement, placedRects, priority) {
  let score = priority * 520
  const rects = placement.positions.map((position) => nodeBounds(position.node, position.x, position.y))

  rects.forEach((rect) => {
    score += overflowPenalty(rect) * 9000

    placedRects.forEach((placed) => {
      const overlap = overlapArea(rect, placed)
      if (overlap > 0) score += 500000 + overlap * 5
    })
  })

  return score
}

function applyClusterPlacement(cluster, placement) {
  const hub = averagePosition(placement.positions)

  placement.positions.forEach((position) => {
    setPosterNode(position.node, position.x, position.y, nodeRadius(position.node), false)
    position.node.clusterId = cluster.id
    position.node.anchorX = position.x
    position.node.anchorY = position.y
    position.node.clusterHubX = hub.x
    position.node.clusterHubY = hub.y
  })

  cluster.hubX = hub.x
  cluster.hubY = hub.y
}

function getCoreLinks(node, links, coreNodes) {
  return coreNodes
    .map((core) => {
      const weight = links.reduce((total, link) => {
        const connected =
          (link.source === node.id && link.target === core.id) ||
          (link.target === node.id && link.source === core.id)
        return connected ? total + link.weight : total
      }, 0)

      return { core, weight }
    })
    .filter((item) => item.weight > 0)
    .sort((a, b) => b.weight - a.weight || a.core.order - b.core.order)
}

function getCoreRelationSignature(node, links, coreNodes) {
  return getCoreLinks(node, links, coreNodes)
    .map((item) => {
      const relations = links
        .filter((link) => {
          return (
            (link.source === node.id && link.target === item.core.id) ||
            (link.target === node.id && link.source === item.core.id)
          )
        })
        .map((link) => link.relation)
        .sort()
        .join('&')

      return `${item.core.id}:${relations}`
    })
    .sort()
    .join('__')
}

function hasInternalLinks(nodes, links) {
  const ids = new Set(nodes.map((node) => node.id))
  return links.some((link) => ids.has(link.source) && ids.has(link.target))
}

function hasCrossCoreSignaturePeer(nodes, links, nonCoreIds, coreSignatureById) {
  const ids = new Set(nodes.map((node) => node.id))

  return links.some((link) => {
    const leftInGroup = ids.has(link.source)
    const rightInGroup = ids.has(link.target)
    if (leftInGroup === rightInGroup) return false

    const insideId = leftInGroup ? link.source : link.target
    const outsideId = leftInGroup ? link.target : link.source
    if (!nonCoreIds.has(outsideId)) return false

    return coreSignatureById.get(insideId) !== coreSignatureById.get(outsideId)
  })
}

function relaxLayout(nodes, coreNodes) {
  resolveNodeCollisions(nodes, coreNodes)
}

function expandLayoutToCanvas(nodes) {
  if (nodes.length < 2) return

  const minX = d3.min(nodes, (node) => node.x) ?? 0
  const maxX = d3.max(nodes, (node) => node.x) ?? VIEW_WIDTH
  const minY = d3.min(nodes, (node) => node.y) ?? 0
  const maxY = d3.max(nodes, (node) => node.y) ?? VIEW_HEIGHT
  const spanX = Math.max(1, maxX - minX)
  const spanY = Math.max(1, maxY - minY)
  const target = {
    left: 150,
    right: VIEW_WIDTH - 150,
    top: 145,
    bottom: VIEW_HEIGHT - 145,
  }
  const targetWidth = target.right - target.left
  const targetHeight = target.bottom - target.top
  const scaleX = Math.max(1, Math.min(1.16, targetWidth / spanX))
  const scaleY = Math.max(1, Math.min(1.42, targetHeight / spanY))
  const sourceCenterX = (minX + maxX) / 2
  const sourceCenterY = (minY + maxY) / 2
  const targetCenterX = (target.left + target.right) / 2
  const targetCenterY = (target.top + target.bottom) / 2

  nodes.forEach((node) => {
    node.x = targetCenterX + (node.x - sourceCenterX) * scaleX
    node.y = targetCenterY + (node.y - sourceCenterY) * scaleY
    keepNodeInBounds(node)
  })
}

function spreadLayoutEvenly(nodes, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))

  nodes.forEach((node) => {
    node.spreadAnchorX = node.x
    node.spreadAnchorY = node.y
  })

  for (let pass = 0; pass < 90; pass += 1) {
    const shifts = new Map(nodes.map((node) => [node.id, { x: 0, y: 0 }]))
    let totalShift = 0

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const left = nodes[i]
        const right = nodes[j]
        const dx = right.x - left.x
        const dy = right.y - left.y
        const distance = Math.hypot(dx, dy) || 1
        const targetDistance = evenNodeDistance(left, right)

        if (distance >= targetDistance) continue

        const pressure = (targetDistance - distance) / targetDistance
        const push = pressure * pressure * 18
        const ux = dx / distance
        const uy = dy / distance
        const leftMobility = coreIds.has(left.id) ? 0.34 : 1
        const rightMobility = coreIds.has(right.id) ? 0.34 : 1
        const leftShift = shifts.get(left.id)
        const rightShift = shifts.get(right.id)

        leftShift.x -= ux * push * leftMobility
        leftShift.y -= uy * push * leftMobility
        rightShift.x += ux * push * rightMobility
        rightShift.y += uy * push * rightMobility
        totalShift += push
      }
    }

    nodes.forEach((node) => {
      const shift = shifts.get(node.id)
      const anchorStrength = coreIds.has(node.id) ? 0.035 : 0.018

      node.x += shift.x + (node.spreadAnchorX - node.x) * anchorStrength
      node.y += shift.y + (node.spreadAnchorY - node.y) * anchorStrength
      keepNodeInBounds(node)
    })

    if (totalShift < 0.18) break
  }

  nodes.forEach((node) => {
    delete node.spreadAnchorX
    delete node.spreadAnchorY
  })
}

function updateClusterHubs(clusters) {
  clusters.forEach((cluster) => {
    const hub = averagePosition(cluster.nodes)
    cluster.hubX = hub.x
    cluster.hubY = hub.y

    cluster.nodes.forEach((node) => {
      node.clusterHubX = hub.x
      node.clusterHubY = hub.y
    })
  })
}

function resolveNodeCollisions(nodes, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))

  for (let pass = 0; pass < 90; pass += 1) {
    let moved = false

    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const left = nodes[i]
        const right = nodes[j]
        const minDistance = minimumNodeDistance(left, right)
        const dx = right.x - left.x
        const dy = right.y - left.y
        const distance = Math.hypot(dx, dy) || 1

        if (distance >= minDistance) continue

        const push = (minDistance - distance) / 2
        const ux = dx / distance
        const uy = dy / distance
        const leftLocked = coreIds.has(left.id)
        const rightLocked = coreIds.has(right.id)

        if (!leftLocked) {
          left.x -= ux * (rightLocked ? push * 2 : push)
          left.y -= uy * (rightLocked ? push * 2 : push)
          keepNodeInBounds(left)
        }

        if (!rightLocked) {
          right.x += ux * (leftLocked ? push * 2 : push)
          right.y += uy * (leftLocked ? push * 2 : push)
          keepNodeInBounds(right)
        }

        moved = true
      }
    }

    nodes.forEach((node) => {
      if (!coreIds.has(node.id)) keepNodeInBounds(node)
    })

    if (!moved) break
  }
}

function minimumNodeDistance(left, right) {
  const sameCluster = left.clusterId && left.clusterId === right.clusterId
  if (left.core || right.core) return left.r + right.r + 80

  return Math.max(
    left.r + right.r + (sameCluster ? 88 : 118),
    (left.plateWidth || 120) / 2 + (right.plateWidth || 120) / 2 + (sameCluster ? 66 : 88),
  )
}

function evenNodeDistance(left, right) {
  const sameCluster = left.clusterId && left.clusterId === right.clusterId
  const base = minimumNodeDistance(left, right)

  if (left.core && right.core) return base + 120
  if (left.core || right.core) return base + 135
  if (sameCluster) return base + 70
  return base + 175
}

function averagePosition(items) {
  const total = items.reduce(
    (sum, item) => ({
      x: sum.x + item.x,
      y: sum.y + item.y,
    }),
    { x: 0, y: 0 },
  )

  return {
    x: total.x / Math.max(1, items.length),
    y: total.y / Math.max(1, items.length),
  }
}

function placementBounds(positions) {
  return positions.reduce(
    (bounds, position) => {
      const rect = nodeBounds(position.node, position.x, position.y)
      return {
        left: Math.min(bounds.left, rect.left),
        right: Math.max(bounds.right, rect.right),
        top: Math.min(bounds.top, rect.top),
        bottom: Math.max(bounds.bottom, rect.bottom),
      }
    },
    { left: Infinity, right: -Infinity, top: Infinity, bottom: -Infinity },
  )
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

function overlapArea(left, right) {
  const width = Math.min(left.right, right.right) - Math.max(left.left, right.left)
  const height = Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top)
  return width > 0 && height > 0 ? width * height : 0
}

function overflowPenalty(rect) {
  return (
    Math.max(0, 82 - rect.left) +
    Math.max(0, rect.right - (VIEW_WIDTH - 82)) +
    Math.max(0, 24 - rect.top) +
    Math.max(0, rect.bottom - (VIEW_HEIGHT - 44))
  )
}

function keepNodeInBounds(node) {
  const bounds = nodeBounds(node)

  if (bounds.left < 82) node.x += 82 - bounds.left
  if (bounds.right > VIEW_WIDTH - 82) node.x -= bounds.right - (VIEW_WIDTH - 82)
  if (bounds.top < 24) node.y += 24 - bounds.top
  if (bounds.bottom > VIEW_HEIGHT - 44) node.y -= bounds.bottom - (VIEW_HEIGHT - 44)
}

function nodeRadius(node) {
  if (node.core) return node.r || 108
  return node.level === 'minor' ? 62 : 74
}

function getPlaqueHeight(node) {
  return node.core ? 62 : 46
}

function getPlaqueOffset(node) {
  return node.r * 1.08 - getPlaqueHeight(node) / 2
}

function setPosterNode(node, x, y, radius, isCore = node.core) {
  node.x = x
  node.y = y
  node.r = radius
  node.plateWidth = getPlateWidth(node.name, isCore)
}

function spreadValue(index, count, min, max) {
  if (count <= 1) return (min + max) / 2
  return min + ((max - min) * index) / (count - 1)
}

function getCorePositions(count) {
  if (count <= 1) return [{ x: VIEW_WIDTH / 2, y: VIEW_HEIGHT * 0.46, role: 'center' }]
  if (count === 2) {
    return [
      { x: VIEW_WIDTH * 0.34, y: VIEW_HEIGHT * 0.46, role: 'left' },
      { x: VIEW_WIDTH * 0.66, y: VIEW_HEIGHT * 0.46, role: 'right' },
    ]
  }

  if (count === 3) {
    return [
      { x: VIEW_WIDTH * 0.32, y: VIEW_HEIGHT * 0.54, role: 'left' },
      { x: VIEW_WIDTH * 0.5, y: VIEW_HEIGHT * 0.26, role: 'top' },
      { x: VIEW_WIDTH * 0.72, y: VIEW_HEIGHT * 0.54, role: 'right' },
    ]
  }

  return d3.range(count).map((index) => {
    const angle = -155 + (310 * index) / Math.max(1, count - 1)
    const point = polarPoint(VIEW_WIDTH / 2, VIEW_HEIGHT * 0.45, 285, angle)

    return {
      x: point.x,
      y: point.y,
      role: point.x < VIEW_WIDTH * 0.42 ? 'left' : point.x > VIEW_WIDTH * 0.58 ? 'right' : 'top',
    }
  })
}

function polarPoint(cx, cy, radius, angleDeg) {
  const angle = (angleDeg * Math.PI) / 180
  return {
    x: cx + Math.cos(angle) * radius,
    y: cy + Math.sin(angle) * radius,
  }
}

function rotateValues(values, amount) {
  return values.map((_, index) => values[(index + amount) % values.length])
}

function getPackMode(cluster) {
  if (cluster.nodes.length === 1) return 'single'
  if (cluster.type === 'bridge') return cluster.nodes.length <= 2 ? 'column' : 'grid'
  if (cluster.type === 'fringe') return cluster.nodes.length <= 3 ? 'row' : 'grid'

  const core = cluster.cores[0]
  if (core?.layoutRole === 'top' && cluster.nodes.length <= 3) return 'row'
  if ((core?.layoutRole === 'left' || core?.layoutRole === 'right') && cluster.nodes.length <= 2) return 'column'
  return 'grid'
}

function getGridColumns(cluster) {
  if (cluster.nodes.length <= 2) return 1

  const core = cluster.cores[0]
  if (cluster.type === 'satellite' && (core?.layoutRole === 'left' || core?.layoutRole === 'right')) {
    return 2
  }

  return cluster.nodes.length <= 4 ? 2 : 3
}

function clusterTypeRank(type) {
  return type === 'bridge' ? 0 : type === 'satellite' ? 1 : 2
}

function drawEdges(edgeLayer, links, nodeById) {
  const edgeGroups = edgeLayer
    .selectAll('g.edge')
    .data(links)
    .join('g')
    .attr('class', 'edge')
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

  edgeGroups
    .append('path')
    .attr('class', 'edge__line-bg')
    .attr('d', (edge, index) => edgePath(edge, nodeById, index))

  edgeGroups
    .append('path')
    .attr('id', (edge) => edge.uid)
    .attr('class', 'edge__line')
    .attr('d', (edge, index) => edgePath(edge, nodeById, index))
    .attr('stroke-width', (edge) => Math.min(3.2, 1.5 + edge.weight * 0.26))
    .attr('marker-start', 'url(#relationArrow)')
    .attr('marker-end', 'url(#relationArrow)')

  edgeGroups
    .append('path')
    .attr('class', 'edge__hit')
    .attr('d', (edge, index) => edgePath(edge, nodeById, index))

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
}

function drawNodes(nodeLayer, nodes, links, nodeById) {
  const nodeGroups = nodeLayer
    .selectAll('g.node')
    .data(nodes)
    .join('g')
    .attr('class', 'node')
    .attr('transform', (node) => `translate(${node.x},${node.y})`)
    .on('mouseenter', (event, node) => {
      setNodeActive(node.id)
      showNodeTooltip(event, node, links, nodeById)
    })
    .on('mousemove', (event, node) => {
      setNodeActive(node.id)
      showNodeTooltip(event, node, links, nodeById)
    })
    .on('mouseleave', () => {
      clearActive()
      hideTooltip()
    })

  nodeGroups.append('circle').attr('class', 'node__halo').attr('r', (node) => node.r + 10)
  nodeGroups.append('circle').attr('class', 'node__ring-outer').attr('r', (node) => node.r + 5)
  nodeGroups.append('circle').attr('class', 'node__ring-inner').attr('r', (node) => node.r)

  nodeGroups
    .append('image')
    .attr('class', 'node__avatar')
    .attr('href', shengAvatar)
    .attr('xlink:href', shengAvatar)
    .attr('x', (node) => -node.r)
    .attr('y', (node) => -node.r * 1.26)
    .attr('width', (node) => node.r * 2)
    .attr('height', (node) => node.r * 2.34)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  nodeGroups
    .append('circle')
    .attr('class', 'node__avatar-border')
    .attr('r', (node) => node.r)

  const plaques = nodeGroups
    .append('g')
    .attr('class', 'node__plaque')
    .attr('transform', (node) => `translate(0,${getPlaqueOffset(node)})`)

  plaques
    .append('path')
    .attr('d', (node) => plaquePath(node.plateWidth, getPlaqueHeight(node)))
    .attr('fill', PLAQUE_COLOR)

  plaques
    .append('path')
    .attr('class', 'node__plaque-border')
    .attr('d', (node) => plaquePath(node.plateWidth, getPlaqueHeight(node)))

  plaques
    .append('text')
    .attr('class', (node) => `node__name ${node.core ? 'node__name--core' : ''}`)
    .attr('y', (node) => getPlaqueHeight(node) * 0.7)
    .attr('text-anchor', 'middle')
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
  const clusterNode = source.core && !target.core ? target : target.core && !source.core ? source : null

  if (clusterNode && Number.isFinite(clusterNode.clusterHubX) && Number.isFinite(clusterNode.clusterHubY)) {
    const hub = { x: clusterNode.clusterHubX, y: clusterNode.clusterHubY }
    const hubDistance = Math.hypot(hub.x - clusterNode.x, hub.y - clusterNode.y)

    if (hubDistance > 14) return hub

    return curvedMidPoint(source, target, index, 72)
  }

  if (!source.core && !target.core && source.clusterId && source.clusterId === target.clusterId) {
    return curvedMidPoint(source, target, index, 58)
  }

  if (source.core && target.core) {
    return curvedMidPoint(source, target, index, 34)
  }

  return null
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

function plaquePath(width, height) {
  const half = width / 2
  const tab = 13
  const corner = 7

  return [
    `M ${-half + corner} 0`,
    `L ${half - corner} 0`,
    `Q ${half} 0 ${half} ${corner}`,
    `L ${half} ${height * 0.32}`,
    `L ${half + tab} ${height / 2}`,
    `L ${half} ${height * 0.68}`,
    `L ${half} ${height - corner}`,
    `Q ${half} ${height} ${half - corner} ${height}`,
    `L ${-half + corner} ${height}`,
    `Q ${-half} ${height} ${-half} ${height - corner}`,
    `L ${-half} ${height * 0.68}`,
    `L ${-half - tab} ${height / 2}`,
    `L ${-half} ${height * 0.32}`,
    `L ${-half} ${corner}`,
    `Q ${-half} 0 ${-half + corner} 0`,
    'Z',
  ].join(' ')
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

  tooltip.title = edge.relation
  tooltip.sub = `${source?.name || edge.source} → ${target?.name || edge.target}`
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

/* 图表舞台区域，也就是 SVG 所在的大容器 */
.relation-network__stage {
  /* 设置为相对定位，方便 tooltip 绝对定位 */
  position: relative;

  /* 占据剩余空间 */
  flex: 1;

  /* 最小高度为 0，避免 flex 布局溢出 */
  min-height: 0;

  /* 超出区域隐藏 */
  overflow: hidden;

  /* 设置圆角 */
  border-radius: 8px;

  /* 设置背景：前两层是浅红网格线，最后一层是画布底色 */
  background:
    linear-gradient(90deg, rgba(142, 47, 36, 0.035) 1px, transparent 1px),
    linear-gradient(0deg, rgba(142, 47, 36, 0.025) 1px, transparent 1px),
    #FDF8EB;

  /* 设置网格背景尺寸 */
  background-size: 34px 34px, 34px 34px, auto;
}

/* SVG 画布 */
.relation-network__svg {
  /* 让 SVG 作为块级元素显示，去除底部空隙 */
  display: block;

  /* SVG 宽度占满容器 */
  width: 100%;

  /* SVG 高度占满容器 */
  height: 100%;

  /* 最小高度为 0，避免撑开布局 */
  min-height: 0;

  /* 鼠标显示抓取样式，提示可以拖动画布 */
  cursor: grab;

  /* 禁止选中文字，避免拖动画布时选中内容 */
  user-select: none;
}

/* SVG 被鼠标按下时 */
.relation-network__svg:active {
  /* 鼠标变成正在抓取的样式 */
  cursor: grabbing;
}

/* 关系线主体 */
:deep(.edge__line) {
  /* 不填充路径内部 */
  fill: none;

  /* 设置关系线颜色 */
  stroke: #8f2f24;

  /* 线条端点为圆角 */
  stroke-linecap: round;

  /* 线条连接处为圆角 */
  stroke-linejoin: round;

  /* 设置透明度 */
  opacity: 0.9;

  /* 给线条加一点投影，让它从背景中浮出来 */
  filter: drop-shadow(0 2px 1px rgba(74, 35, 15, 0.18));
}

/* 关系线底部金色衬线 */
:deep(.edge__line-bg) {
  /* 不填充路径内部 */
  fill: none;

  /* 设置底线为金色 */
  stroke: #d8ad4b;

  /* 底线更粗，用来形成描边效果 */
  stroke-width: 6.5;

  /* 线条端点为圆角 */
  stroke-linecap: round;

  /* 线条连接处为圆角 */
  stroke-linejoin: round;

  /* 降低透明度，避免太抢眼 */
  opacity: 0.24;
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

/* 激活状态下的关系线 */
:deep(.edge.is-active .edge__line) {
  /* 激活线条完全显示 */
  opacity: 1;

  /* 添加金色光晕和阴影 */
  filter:
    drop-shadow(0 0 4px rgba(255, 223, 134, 0.8))
    drop-shadow(0 3px 4px rgba(86, 37, 13, 0.24));
}

/* 激活状态下关系线底部衬线 */
:deep(.edge.is-active .edge__line-bg) {
  /* 提高底线透明度 */
  opacity: 0.52;
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

/* 节点外圈 */
:deep(.node__ring-outer) {
  /* 设置浅米色填充 */
  fill: rgba(255, 244, 213, 0.72);

  /* 使用 SVG 中定义的金色渐变描边 */
  stroke: url(#plateGold);

  /* 设置外圈描边宽度 */
  stroke-width: 7;

  /* 使用 SVG 中定义的阴影滤镜 */
  filter: url(#nodeShadow);
}

/* 节点内圈 */
:deep(.node__ring-inner) {
  /* 设置半透明米黄色填充 */
  fill: rgba(248, 230, 189, 0.58);

  /* 设置深金棕色描边 */
  stroke: #7a4b19;

  /* 设置描边宽度 */
  stroke-width: 2.2;
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

/* 名牌边框 */
:deep(.node__plaque-border) {
  /* 不填充，只显示边框 */
  fill: none;

  /* 使用金色渐变描边 */
  stroke: url(#plateGold);

  /* 设置边框宽度 */
  stroke-width: 3.2;
}

/* 人物姓名文字 */
:deep(.node__name) {
  /* 设置姓名文字颜色 */
  fill: #fff1bf;

  /* 设置普通节点姓名字号 */
  font-size: 26px;

  /* 字体加粗 */
  font-weight: 900;

  /* 先描边再填充，增强文字清晰度 */
  paint-order: stroke;

  /* 设置文字深色描边 */
  stroke: rgba(46, 20, 10, 0.5);

  /* 设置文字描边宽度 */
  stroke-width: 2px;

  /* 设置描边连接处圆润 */
  stroke-linejoin: round;

  /* 禁止姓名文字响应鼠标事件 */
  pointer-events: none;
}

/* 核心人物姓名文字 */
:deep(.node__name--core) {
  /* 核心人物名字更大 */
  font-size: 38px;
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
</style>
