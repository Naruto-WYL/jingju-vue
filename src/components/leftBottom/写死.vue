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
const VIEW_WIDTH = 1120
const VIEW_HEIGHT = 700
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
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (drawFrame) cancelAnimationFrame(drawFrame)
  d3.select(svgRef.value).selectAll('*').remove()
})

watch([currentGraph, selectedScript], async () => {
  await nextTick()
  scheduleDraw()
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
      r: isCore ? 58 : isMajor ? 46 : 38,
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
        node.r = 58
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
  return Math.max(isCore ? 116 : 88, Math.min(isCore ? 160 : 128, charCount * 24 + 32))
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
    uid: `node-${index}`,
  }))
  const links = currentGraph.value.links.map((link, index) => ({
    ...link,
    uid: `edge-${index}`,
  }))

  const nodeById = new Map(nodes.map((node) => [node.id, node]))
  layoutGraph(nodes, links, nodeById)
  fitViewBox(svg, nodes)

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
    .attr('orient', 'auto')
    .attr('markerUnits', 'strokeWidth')
    .append('path')
    .attr('d', 'M1.5,2 L10,6 L1.5,10 Z')
    .attr('fill', EDGE_COLOR)
}

function fitViewBox(svg, nodes) {
  const stage = chartRef.value
  const targetAspect = stage?.clientWidth && stage?.clientHeight
    ? stage.clientWidth / stage.clientHeight
    : VIEW_WIDTH / VIEW_HEIGHT
  const pad = 30

  let minX = d3.min(nodes, (node) => node.x - Math.max(node.r * 1.1, node.plateWidth / 2 + 18)) ?? 0
  let maxX = d3.max(nodes, (node) => node.x + Math.max(node.r * 1.1, node.plateWidth / 2 + 18)) ?? VIEW_WIDTH
  let minY = d3.min(nodes, (node) => node.y - node.r * 1.28 - 20) ?? 0
  let maxY = d3.max(nodes, (node) => node.y + node.r + (node.core ? 96 : 82)) ?? VIEW_HEIGHT

  minX -= pad
  maxX += pad
  minY -= pad
  maxY += pad

  let boxWidth = maxX - minX
  let boxHeight = maxY - minY
  const boxAspect = boxWidth / boxHeight

  if (boxAspect > targetAspect) {
    const nextHeight = boxWidth / targetAspect
    const extra = nextHeight - boxHeight
    minY -= extra / 2
    boxHeight = nextHeight
  } else {
    const nextWidth = boxHeight * targetAspect
    const extra = nextWidth - boxWidth
    minX -= extra / 2
    boxWidth = nextWidth
  }

  svg.attr('viewBox', `${minX} ${minY} ${boxWidth} ${boxHeight}`)
}

function layoutGraph(nodes, links, nodeById) {
  const coreNodes = nodes
    .filter((node) => node.core)
    .sort((a, b) => b.score - a.score || b.degree - a.degree)
  const minLayoutX = -120
  const maxLayoutX = VIEW_WIDTH + 120
  const minLayoutY = -90
  const maxLayoutY = VIEW_HEIGHT + 135

  const corePositions = getCorePositions(coreNodes.length)
  coreNodes.forEach((node, index) => {
    const point = corePositions[index] || corePositions[corePositions.length - 1]
    node.anchorX = point.x
    node.anchorY = point.y
    node.x = point.x
    node.y = point.y
  })

  const assigned = assignPeripheralNodes(nodes, links, coreNodes)

  assigned.forEach((groupNodes, coreId) => {
    const core = nodeById.get(coreId)
    const spread = angleSpreadForCore(core)

    groupNodes
      .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, 'zh-Hans-CN'))
      .forEach((node, index) => {
        const rings = groupNodes.length > 6 ? 2 : 1
        const perRing = Math.ceil(groupNodes.length / rings)
        const ringIndex = Math.floor(index / perRing)
        const localIndex = index % perRing
        const localCount = Math.min(perRing, groupNodes.length - ringIndex * perRing)
        const t = localCount === 1 ? 0.5 : localIndex / (localCount - 1)
        const ringShift = ringIndex ? (spread.end - spread.start) / Math.max(8, localCount * 2) : 0
        const angle = spread.start + (spread.end - spread.start) * t + ringShift
        const radius = 230 + ringIndex * 102 + (node.level === 'minor' ? 24 : 0)
        const point = polarPoint(core.anchorX, core.anchorY, radius, angle)
        node.anchorX = clamp(point.x, minLayoutX, maxLayoutX)
        node.anchorY = clamp(point.y, minLayoutY, maxLayoutY)
        node.x = node.anchorX
        node.y = node.anchorY
      })
  })

  const unanchored = nodes.filter((node) => !Number.isFinite(node.anchorX))
  unanchored.forEach((node, index) => {
    const angle = -150 + (300 * index) / Math.max(1, unanchored.length - 1)
    const point = polarPoint(VIEW_WIDTH / 2, VIEW_HEIGHT / 2, 310, angle)
    node.anchorX = clamp(point.x, minLayoutX, maxLayoutX)
    node.anchorY = clamp(point.y, minLayoutY, maxLayoutY)
    node.x = node.anchorX
    node.y = node.anchorY
  })

  coreNodes.forEach((node) => {
    node.fx = node.anchorX
    node.fy = node.anchorY
  })

  const simulation = d3
    .forceSimulation(nodes)
    .force('charge', d3.forceManyBody().strength((node) => (node.core ? -180 : -110)))
    .force('x', d3.forceX((node) => node.anchorX).strength((node) => (node.core ? 1 : 0.72)))
    .force('y', d3.forceY((node) => node.anchorY).strength((node) => (node.core ? 1 : 0.72)))
    .force('collision', d3.forceCollide((node) => nodeCollisionRadius(node)).strength(1))
    .stop()

  for (let i = 0; i < 220; i += 1) {
    simulation.tick()
  }

  nodes.forEach((node) => {
    node.fx = null
    node.fy = null
    node.x = clamp(node.x, minLayoutX, maxLayoutX)
    node.y = clamp(node.y, minLayoutY, maxLayoutY)
  })
}

function nodeCollisionRadius(node) {
  return Math.max(node.r + 62, node.plateWidth / 2 + 34)
}

function getCorePositions(count) {
  if (count <= 1) return [{ x: VIEW_WIDTH / 2, y: VIEW_HEIGHT * 0.44 }]
  if (count === 2) {
    return [
      { x: VIEW_WIDTH * 0.36, y: VIEW_HEIGHT * 0.48 },
      { x: VIEW_WIDTH * 0.67, y: VIEW_HEIGHT * 0.47 },
    ]
  }

  return [
    { x: VIEW_WIDTH * 0.35, y: VIEW_HEIGHT * 0.5 },
    { x: VIEW_WIDTH * 0.53, y: VIEW_HEIGHT * 0.27 },
    { x: VIEW_WIDTH * 0.72, y: VIEW_HEIGHT * 0.5 },
    { x: VIEW_WIDTH * 0.2, y: VIEW_HEIGHT * 0.52 },
    { x: VIEW_WIDTH * 0.55, y: VIEW_HEIGHT * 0.68 },
  ]
}

function assignPeripheralNodes(nodes, links, coreNodes) {
  const coreIds = new Set(coreNodes.map((node) => node.id))
  const assigned = new Map(coreNodes.map((node) => [node.id, []]))

  nodes
    .filter((node) => !coreIds.has(node.id))
    .forEach((node) => {
      let bestCore = coreNodes[0]?.id
      let bestScore = -Infinity

      coreNodes.forEach((core) => {
        const score = links.reduce((total, link) => {
          const connected =
            (link.source === node.id && link.target === core.id) ||
            (link.target === node.id && link.source === core.id)
          return connected ? total + link.weight : total
        }, 0)

        if (score > bestScore) {
          bestCore = core.id
          bestScore = score
        }
      })

      if (bestCore) {
        assigned.get(bestCore).push(node)
      }
    })

  return assigned
}

function angleSpreadForCore(core) {
  if (!core) return { start: -160, end: 160 }

  const xZone = core.anchorX / VIEW_WIDTH
  const yZone = core.anchorY / VIEW_HEIGHT

  if (yZone < 0.34) return { start: -170, end: 10 }
  if (xZone < 0.48) return { start: 130, end: 290 }
  if (xZone > 0.62) return { start: -62, end: 92 }
  return { start: 35, end: 325 }
}

function polarPoint(cx, cy, radius, angleDeg) {
  const angle = (angleDeg * Math.PI) / 180
  return {
    x: cx + Math.cos(angle) * radius,
    y: cy + Math.sin(angle) * radius,
  }
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
    .attr('stroke-width', (edge) => Math.min(2.7, 1.25 + edge.weight * 0.22))
    .attr('marker-end', 'url(#relationArrow)')

  edgeGroups
    .append('path')
    .attr('class', 'edge__hit')
    .attr('d', (edge, index) => edgePath(edge, nodeById, index))

  const labels = edgeGroups
    .append('text')
    .attr('class', 'edge__label')
    .attr('dy', -7)

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
    .attr('transform', (node) => `translate(0,${node.r + (node.core ? 30 : 24)})`)

  plaques
    .append('path')
    .attr('d', (node) => plaquePath(node.plateWidth, node.core ? 42 : 34))
    .attr('fill', PLAQUE_COLOR)

  plaques
    .append('path')
    .attr('class', 'node__plaque-border')
    .attr('d', (node) => plaquePath(node.plateWidth, node.core ? 42 : 34))

  plaques
    .append('text')
    .attr('class', (node) => `node__name ${node.core ? 'node__name--core' : ''}`)
    .attr('y', (node) => (node.core ? 28 : 23))
    .attr('text-anchor', 'middle')
    .text((node) => node.name)
}

function edgePath(edge, nodeById, index) {
  const source = nodeById.get(edge.source)
  const target = nodeById.get(edge.target)
  if (!source || !target) return ''

  const dx = target.x - source.x
  const dy = target.y - source.y
  const distance = Math.hypot(dx, dy) || 1
  const sx = source.x + (dx / distance) * (source.r + 14)
  const sy = source.y + (dy / distance) * (source.r + 14)
  const tx = target.x - (dx / distance) * (target.r + 16)
  const ty = target.y - (dy / distance) * (target.r + 16)
  const mx = (sx + tx) / 2
  const my = (sy + ty) / 2
  const bendSign = index % 2 === 0 ? 1 : -1
  const bendSize = Math.min(62, 18 + distance * 0.06)
  const nx = -dy / distance
  const ny = dx / distance
  const cx = mx + nx * bendSize * bendSign
  const cy = my + ny * bendSize * bendSign

  return `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`
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
  background: transparent;
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
  stroke-width: 5.2;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.28;
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
  font-size: 15px;
  font-weight: 900;
  opacity: 0;
  paint-order: stroke;
  stroke: rgba(255, 245, 218, 0.95);
  stroke-width: 4px;
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
  stroke-width: 3;
  stroke-dasharray: 8 6;
}

:deep(.node__ring-outer) {
  fill: rgba(255, 244, 213, 0.72);
  stroke: url(#plateGold);
  stroke-width: 4.4;
  filter: url(#nodeShadow);
}

:deep(.node__ring-inner) {
  fill: rgba(248, 230, 189, 0.58);
  stroke: #7a4b19;
  stroke-width: 1.2;
}

:deep(.node__avatar) {
  pointer-events: none;
  overflow: visible;
}

:deep(.node__avatar-border) {
  fill: none;
  stroke: #6b421b;
  stroke-width: 1.6;
}

:deep(.node__plaque) {
  filter: drop-shadow(0 4px 3px rgba(70, 30, 12, 0.28));
}

:deep(.node__plaque-border) {
  fill: none;
  stroke: url(#plateGold);
  stroke-width: 2.2;
}

:deep(.node__name) {
  fill: #fff1bf;
  font-size: 20px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(46, 20, 10, 0.5);
  stroke-width: 2px;
  stroke-linejoin: round;
  pointer-events: none;
}

:deep(.node__name--core) {
  font-size: 26px;
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
