<template>
  <div class="evolution-sankey">
    <div ref="chartRef" class="sankey-wrap">
      <svg
        ref="svgRef"
        class="sankey-svg"
        role="img"
        aria-label="历史时期、身份类型与行当的桑基图"
      ></svg>

      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">
        {{ errorMessage }}
      </div>
      <div v-else-if="!rows.length" class="chart-state">暂无桑基图数据</div>
    </div>

    <!-- Tooltip 放到 body 外层，避免被遮挡 -->
    <Teleport to="body">
      <div
        ref="tooltipRef"
        class="sankey-tooltip"
        :class="{ 'is-visible': tooltip.show }"
        :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
      >
        <strong>{{ tooltip.title }}</strong>
        <span>{{ tooltip.value }}</span>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as d3 from 'd3'
import { sankey, sankeyJustify, sankeyLinkHorizontal } from 'd3-sankey'

const DATA_URL = '/数据表合集/1/Table3_Historical_Evolution.csv'
const PERIOD_FIELD = '历史时期'
const IDENTITY_FIELD = '身份类型(角色)'
const PERIOD_SHARE_FIELD = '该身份在此时期的占比'
const FIXED_FIELDS = new Set([PERIOD_FIELD, IDENTITY_FIELD, PERIOD_SHARE_FIELD])

const typeColors = {
  period: '#9d5b46',
  identity: '#b98539',
  trade: '#476f86',
}

const chartRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)
const rows = ref([])
const loading = ref(false)
const errorMessage = ref('')

const tooltip = reactive({
  show: false,
  x: 0,
  y: 0,
  title: '',
  value: '',
})

let resizeFrame = 0

onMounted(async () => {
  await loadRows()
  await nextTick()
  drawSankey()
  window.addEventListener('resize', scheduleDraw)
})

onBeforeUnmount(() => {
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  window.removeEventListener('resize', scheduleDraw)
})

async function loadRows() {
  loading.value = true
  errorMessage.value = ''
  try {
    rows.value = await d3.csv(encodeURI(DATA_URL), normalizeRow)
  } catch (error) {
    errorMessage.value = 'Table3_Historical_Evolution.csv 加载失败'
    console.error(error)
  } finally {
    loading.value = false
  }
}

function normalizeRow(row) {
  const normalized = {
    period: cleanText(row[PERIOD_FIELD]),
    identity: cleanText(row[IDENTITY_FIELD]),
    periodShare: parseNumber(row[PERIOD_SHARE_FIELD]),
    trades: {},
  }

  Object.keys(row)
    .filter((key) => !FIXED_FIELDS.has(key))
    .forEach((trade) => {
      const value = parseNumber(row[trade])
      if (value > 0) normalized.trades[cleanText(trade)] = value
    })

  return normalized
}

function drawSankey() {
  if (!svgRef.value || !chartRef.value || !rows.value.length) return

  const bounds = chartRef.value.getBoundingClientRect()
  const width = Math.max(420, bounds.width || 680)
  const height = Math.max(300, bounds.height || 360)

  const margin = {
    top: 34,
    right: 30,
    bottom: 14,
    left: 20,
  }

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()
  hideTooltip()

  const graph = buildGraph(rows.value)
  if (!graph.nodes.length || !graph.links.length) return

  svg.attr('viewBox', `0 0 ${width} ${height}`).attr('preserveAspectRatio', 'none')

  const layout = sankey()
    .nodeId((node) => node.id)
    .nodeAlign(sankeyJustify)
    .nodeWidth(12)
    .nodePadding(12)
    .nodeSort((a, b) => sortByType(a, b))
    .extent([
      [margin.left, margin.top],
      [width - margin.right, height - margin.bottom],
    ])

  const sankeyGraph = layout({
    nodes: graph.nodes.map((node) => ({ ...node })),
    links: graph.links.map((link) => ({ ...link })),
  })

  drawColumnLabels(svg, sankeyGraph.nodes)
  drawLinks(svg, sankeyGraph.links)
  drawNodes(svg, sankeyGraph.nodes)
}

function scheduleDraw() {
  if (resizeFrame) cancelAnimationFrame(resizeFrame)
  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = 0
    drawSankey()
  })
}

function buildGraph(sourceRows) {
  const nodes = new Map()
  const links = new Map()

  sourceRows.forEach((row) => {
    if (!row.period || !row.identity || row.periodShare <= 0) return

    const periodId = addNode(nodes, 'period', row.period)
    const identityId = addNode(nodes, 'identity', row.identity)
    addLink(links, periodId, identityId, row.periodShare, `${row.period} -> ${row.identity}`)

    Object.entries(row.trades).forEach(([trade, tradeShare]) => {
      const tradeId = addNode(nodes, 'trade', trade)
      const weightedValue = (row.periodShare * tradeShare) / 100
      addLink(links, identityId, tradeId, weightedValue, `${row.identity} -> ${trade}`)
    })
  })

  return {
    nodes: Array.from(nodes.values()),
    links: Array.from(links.values()).filter((link) => link.value > 0),
  }
}

function addNode(nodes, type, label) {
  const id = `${type}:${label}`
  if (!nodes.has(id)) {
    nodes.set(id, { id, type, label })
  }
  return id
}

function addLink(links, source, target, value, label) {
  const key = `${source}=>${target}`
  const current = links.get(key)
  if (current) {
    current.value += value
  } else {
    links.set(key, { source, target, value, label })
  }
}

function drawColumnLabels(svg, nodes) {
  const labels = [
    { type: 'period', text: '历史时期' },
    { type: 'identity', text: '身份类型' },
    { type: 'trade', text: '行当' },
  ]

  labels.forEach((item) => {
    const columnNodes = nodes.filter((node) => node.type === item.type)
    if (!columnNodes.length) return
    const x = d3.mean(columnNodes, (node) => (node.x0 + node.x1) / 2)

    svg
      .append('text')
      .attr('class', 'column-label')
      .attr('x', x)
      .attr('y', 16)
      .attr('text-anchor', 'middle')
      .text(item.text)
  })
}

function drawLinks(svg, links) {
  const defs = svg.append('defs')
  const linkPath = sankeyLinkHorizontal()

  links.forEach((link, index) => {
    const gradient = defs
      .append('linearGradient')
      .attr('id', `sankey-gradient-${index}`)
      .attr('gradientUnits', 'userSpaceOnUse')
      .attr('x1', link.source.x1)
      .attr('x2', link.target.x0)

    gradient.append('stop').attr('offset', '0%').attr('stop-color', getNodeColor(link.source))
    gradient.append('stop').attr('offset', '100%').attr('stop-color', getNodeColor(link.target))
  })

  svg
    .append('g')
    .attr('class', 'links')
    .selectAll('path')
    .data(links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', linkPath)
    .attr('stroke', (_, index) => `url(#sankey-gradient-${index})`)
    .attr('stroke-width', (link) => Math.max(1, link.width))
    .on('mouseenter', (event, link) => {
      highlightLink(link)
      showTooltip(event, link.label, `映射占比：${formatPercent(link.value)}`)
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', () => {
      clearHighlight()
      hideTooltip()
    })
}

function drawNodes(svg, nodes) {
  const node = svg
    .append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'sankey-node')

  node.append('title').text((d) => `${d.label} ${formatPercent(d.value)}`)

  node
    .append('rect')
    .attr('x', (d) => d.x0)
    .attr('y', (d) => d.y0)
    .attr('width', (d) => Math.max(1, d.x1 - d.x0))
    .attr('height', (d) => Math.max(2, d.y1 - d.y0))
    .attr('rx', 4)
    .attr('fill', getNodeColor)
    .on('mouseenter', (event, d) => {
      highlightNode(d)
      d3.select(event.currentTarget).attr('filter', 'brightness(1.08)')
      showTooltip(event, d.label, `节点总占比：${formatPercent(d.value)}`)
    })
    .on('mousemove', moveTooltip)
    .on('mouseleave', (event) => {
      clearHighlight()
      d3.select(event.currentTarget).attr('filter', null)
      hideTooltip()
    })

  node
    .append('text')
    .attr('x', getLabelX)
    .attr('y', (d) => (d.y0 + d.y1) / 2)
    .attr('dy', '0.32em')
    .attr('text-anchor', getLabelAnchor)
    .text((d) => d.label)
}

// 高亮节点和连线
function highlightNode(targetNode) {
  const svg = d3.select(svgRef.value)
  const relatedNodeIds = new Set([targetNode.id])

  svg.selectAll('.sankey-link').attr('stroke-opacity', (link) => {
    const isRelated = link.source.id === targetNode.id || link.target.id === targetNode.id
    if (isRelated) {
      relatedNodeIds.add(link.source.id)
      relatedNodeIds.add(link.target.id)
    }
    return isRelated ? 0.76 : 0.06
  })

  svg.selectAll('.sankey-node').attr('opacity', (node) =>
    relatedNodeIds.has(node.id) ? 1 : 0.16
  )
}

function highlightLink(targetLink) {
  const svg = d3.select(svgRef.value)
  const sourceId = targetLink.source.id
  const targetId = targetLink.target.id

  svg.selectAll('.sankey-link').attr('stroke-opacity', (link) =>
    link === targetLink ? 0.82 : 0.06
  )

  svg.selectAll('.sankey-node').attr('opacity', (node) =>
    node.id === sourceId || node.id === targetId ? 1 : 0.16
  )
}

function clearHighlight() {
  const svg = d3.select(svgRef.value)
  svg.selectAll('.sankey-link').attr('stroke-opacity', null)
  svg.selectAll('.sankey-node').attr('opacity', 1)
}

// Tooltip
function showTooltip(event, title, value) {
  tooltip.title = title
  tooltip.value = value
  tooltip.show = true
  moveTooltip(event)
}

function moveTooltip(event) {
  const offset = 14
  const tooltipWidth = 190
  const tooltipHeight = 70

  let x = event.clientX + offset
  let y = event.clientY + offset

  if (x + tooltipWidth > window.innerWidth) x = event.clientX - tooltipWidth - offset
  if (y + tooltipHeight > window.innerHeight) y = event.clientY - tooltipHeight - offset

  tooltip.x = x
  tooltip.y = y
}

function hideTooltip() {
  tooltip.show = false
}

function getNodeColor(node) {
  return typeColors[node.type] || '#7d7469'
}

function getLabelX(node) {
  return node.x1 + 5
}

function getLabelAnchor() {
  return 'start'
}

function sortByType(a, b) {
  if (a.type !== b.type) return a.type.localeCompare(b.type)
  return a.label.localeCompare(b.label, 'zh-Hans-CN')
}

function cleanText(value) {
  return String(value ?? '').trim()
}

function parseNumber(value) {
  const parsed = Number.parseFloat(String(value ?? '').replace('%', '').trim())
  return Number.isFinite(parsed) ? parsed : 0
}

function formatPercent(value) {
  return `${d3.format('.2f')(value)}%`
}
</script>

<style scoped>
.evolution-sankey {
  position: relative;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  gap: 8px;
  color: #3d3935;
}

.sankey-wrap {
  position: relative;
  min-height: 310px;
  flex: 1;
  overflow: hidden;
}

.sankey-svg {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 310px;
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: rgba(61, 57, 53, 0.72);
  font-size: 12px;
  pointer-events: none;
}

.chart-state--error {
  color: #9d2f2a;
}

.sankey-tooltip {
  position: fixed;
  z-index: 9999;
  display: grid;
  gap: 5px;
  max-width: 180px;
  padding: 8px 10px;
  border: 1px solid rgba(111, 20, 24, 0.18);
  border-radius: 6px;
  background: rgba(255, 250, 241, 0.96);
  box-shadow: 0 8px 18px rgba(72, 47, 30, 0.14);
  color: #3d3935;
  font-size: 11px;
  line-height: 1.35;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.sankey-tooltip.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.sankey-tooltip strong {
  font-size: 12px;
}

.sankey-tooltip span {
  color: rgba(61, 57, 53, 0.72);
}

:deep(.column-label) {
  fill: rgba(61, 57, 53, 0.72);
  font-size: 11px;
  font-weight: 700;
}

:deep(.sankey-link) {
  fill: none;
  mix-blend-mode: multiply;
  stroke-linecap: round;
  stroke-opacity: 0.34;
  transition: stroke-opacity 0.18s ease;
}

:deep(.sankey-node) {
  transition: opacity 0.18s ease;
}

:deep(.sankey-node rect) {
  cursor: pointer;
  opacity: 0.94;
  stroke: rgba(255, 255, 255, 0.7);
  stroke-width: 1;
}

:deep(.sankey-node text) {
  fill: rgba(61, 57, 53, 0.86);
  font-size: 10px;
  font-weight: 600;
  paint-order: stroke;
  pointer-events: none;
  stroke: rgba(255, 250, 241, 0.86);
  stroke-width: 3px;
}
</style>