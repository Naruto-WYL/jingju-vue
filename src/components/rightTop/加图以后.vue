<template>
  <div class="relation-network">
    <div class="relation-network__toolbar">
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

defineProps({
  arcRelations: {
    type: Object,
    default: () => ({}),
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
  layoutGraph(nodes, links, nodeById)
  svg.attr('viewBox', `0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`)

  const defs = svg.append('defs')
  drawDefs(defs)

  const viewport = svg.append('g').attr('class', 'network-viewport')
  svg.call(
    d3
      .zoom()
      .scaleExtent([0.72, 2.4])
      .on('zoom', (event) => {
        viewport.attr('transform', event.transform)
      }),
  )

  const edgeLayer = viewport.append('g').attr('class', 'edge-layer')
  const nodeLayer = viewport.append('g').attr('class', 'node-layer')

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

function layoutGraph(nodes, links) {
  layoutPosterGraph(nodes, links)
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
    .attr('class', (node) => `node ${node.core ? 'node--core' : ''}`)
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
.relation-network {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #273b58;
  font-family:
    "STKaiti",
    "KaiTi",
    "Microsoft YaHei",
    "PingFang SC",
    sans-serif;
}

.relation-network__toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 32px;
}

.script-select {
  width: min(240px, 52%);
  height: 30px;
  padding: 0 32px 0 12px;
  border: 1px solid rgba(142, 47, 36, 0.38);
  border-radius: 6px;
  outline: none;
  background:
    linear-gradient(180deg, rgba(255, 248, 232, 0.94), rgba(242, 224, 188, 0.94)),
    #f4e8cf;
  color: #50301c;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.script-select:focus {
  border-color: rgba(142, 47, 36, 0.74);
  box-shadow: 0 0 0 2px rgba(212, 166, 74, 0.24);
}

.relation-network__stage {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 8px;
  background:
    linear-gradient(90deg, rgba(142, 47, 36, 0.035) 1px, transparent 1px),
    linear-gradient(0deg, rgba(142, 47, 36, 0.025) 1px, transparent 1px),
    #f6ecd6;
  background-size: 34px 34px, 34px 34px, auto;
}

.relation-network__svg {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
  cursor: grab;
  user-select: none;
}

.relation-network__svg:active {
  cursor: grabbing;
}

:deep(.edge__line) {
  fill: none;
  stroke: #8f2f24;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.9;
  filter: drop-shadow(0 2px 1px rgba(74, 35, 15, 0.18));
}

:deep(.edge__line-bg) {
  fill: none;
  stroke: #d8ad4b;
  stroke-width: 6.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.24;
}

:deep(.edge__hit) {
  fill: none;
  stroke: transparent;
  stroke-width: 24;
  pointer-events: stroke;
  cursor: pointer;
}

:deep(.edge__label) {
  fill: #22140d;
  font-size: 26px;
  font-weight: 900;
  opacity: 0;
  paint-order: stroke;
  stroke: rgba(255, 245, 218, 0.95);
  stroke-width: 6px;
  stroke-linejoin: round;
  pointer-events: none;
  transition: opacity 0.18s ease;
}

:deep(.edge),
:deep(.node) {
  transition:
    opacity 0.2s ease,
    filter 0.2s ease;
}

:deep(.edge.is-muted),
:deep(.node.is-muted) {
  opacity: 0.16;
}

:deep(.edge.is-active .edge__line) {
  opacity: 1;
  filter:
    drop-shadow(0 0 4px rgba(255, 223, 134, 0.8))
    drop-shadow(0 3px 4px rgba(86, 37, 13, 0.24));
}

:deep(.edge.is-active .edge__line-bg) {
  opacity: 0.52;
}

:deep(.edge.is-active .edge__label) {
  opacity: 1;
}

:deep(.node) {
  cursor: pointer;
}

:deep(.node__halo) {
  fill: rgba(255, 238, 184, 0.22);
  stroke: rgba(212, 166, 74, 0.65);
  stroke-width: 4;
  stroke-dasharray: 12 8;
}

:deep(.node__ring-outer) {
  fill: rgba(255, 244, 213, 0.72);
  stroke: url(#plateGold);
  stroke-width: 7;
  filter: url(#nodeShadow);
}

:deep(.node__ring-inner) {
  fill: rgba(248, 230, 189, 0.58);
  stroke: #7a4b19;
  stroke-width: 2.2;
}

:deep(.node__avatar) {
  pointer-events: none;
  overflow: visible;
}

:deep(.node__avatar-border) {
  fill: none;
  stroke: #6b421b;
  stroke-width: 3;
}

:deep(.node__plaque) {
  filter: drop-shadow(0 4px 3px rgba(70, 30, 12, 0.28));
}

:deep(.node__plaque-border) {
  fill: none;
  stroke: url(#plateGold);
  stroke-width: 3.2;
}

:deep(.node__name) {
  fill: #fff1bf;
  font-size: 26px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(46, 20, 10, 0.5);
  stroke-width: 2px;
  stroke-linejoin: round;
  pointer-events: none;
}

:deep(.node__name--core) {
  font-size: 38px;
}

:deep(.node.is-active) {
  filter:
    drop-shadow(0 0 9px rgba(255, 224, 142, 0.9))
    drop-shadow(0 8px 12px rgba(90, 36, 13, 0.25));
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6a4526;
  font-size: 14px;
  font-weight: 800;
  pointer-events: none;
}

.chart-state--error {
  color: #9b2b24;
}

.relation-tooltip {
  position: absolute;
  z-index: 10;
  width: 260px;
  max-width: calc(100% - 20px);
  padding: 10px 12px;
  border: 1px solid rgba(142, 47, 36, 0.46);
  border-radius: 8px;
  background: rgba(255, 249, 232, 0.97);
  box-shadow: 0 10px 24px rgba(50, 24, 10, 0.22);
  color: #3a2113;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

.relation-tooltip.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.relation-tooltip strong,
.relation-tooltip span,
.relation-tooltip p {
  display: block;
}

.relation-tooltip strong {
  color: #8f2f24;
  font-size: 17px;
  line-height: 1.35;
}

.relation-tooltip span {
  margin-top: 3px;
  color: #76502b;
  font-size: 12px;
  font-weight: 800;
}

.relation-tooltip p {
  margin: 6px 0 0;
  color: #3a2113;
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 760px) {
  .relation-network__toolbar {
    justify-content: flex-start;
  }

  .script-select {
    width: 100%;
  }

  .relation-network__svg {
    min-width: 920px;
  }
}
</style>
