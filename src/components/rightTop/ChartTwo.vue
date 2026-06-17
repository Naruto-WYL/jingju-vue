<template>
  <div ref="panelRef" class="scatter-panel">
    <svg ref="svgRef" class="scatter-chart" role="img" aria-label="网络结构散点图" />

    <div v-if="loading" class="chart-state">数据加载中...</div>
    <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
    <div v-else-if="!points.length" class="chart-state">暂无散点数据</div>

    <button v-if="activeFilterLabel" class="scatter-return-btn" type="button" @click="returnToFullScatter">
      返回全图
    </button>

    <div ref="tooltipRef" class="scatter-tooltip" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import { clearLoopFilter, loopFilterState } from '../../services/loopFilterStore'

const H = {
  scriptId: '\u5267\u672cID',
  title: '\u5267\u76ee\u540d\u79f0',
  category: '\u5267\u76ee\u7c7b\u522b',
  weight: '\u5185\u5bb9\u91cf\u6743\u91cd',
  density: '\u7f51\u7edc\u5bc6\u5ea6',
  centralization: '\u5ea6\u4e2d\u5fc3\u5316',
  nodeCount: '\u7f51\u7edc\u8282\u70b9\u6570',
  edgeCount: '\u7f51\u7edc\u8fb9\u6570\u4f30\u8ba1',
  roleCount: '\u89d2\u8272\u6570',
  primaryRelation: '\u4e3b\u89d2\u8272\u5173\u7cfb',
  primaryTheme: '\u4e3b\u4e3b\u9898',
  relation: '\u89d2\u8272\u5173\u7cfb\u7c7b\u578b',
  theme: '\u4e3b\u9898',
  narrative: '\u53d9\u4e8b\u7ed3\u6784\u7ebf',
  wave: '\u6ce2\u52a8\u578b',
  outcome: '\u5173\u7cfb\u6f14\u5316\u7ed3\u5c40',
  flowId: '\u95ed\u73afID',
}

const SCATTER_URL = '/data/script_scatter_loop_metrics.csv'
const LINKAGE_URL = '/data/script_loop_linkage_long.csv'
const width = 760
const height = 700
const margin = { top: 12, right: 20, bottom: 120, left: 80 }
const chartUid = `script-scatter-${Math.random().toString(36).slice(2, 10)}`

const categoryColors = new Map([
  ['公案戏', '#d0a53c'],
  ['家庭戏', '#e68a57'],
  ['江湖戏', '#5f82c8'],
  ['历史戏', '#d84f5d'],
  ['神怪戏', '#36a8b6'],
])

const svgRef = ref(null)
const panelRef = ref(null)
const tooltipRef = ref(null)
const rows = ref([])
const linkageRows = ref([])
const loading = ref(false)
const errorMessage = ref('')
let resizeObserver = null
let drawFrame = 0
let lastPanelWidth = 0
let lastPanelHeight = 0

defineProps({
  plays: {
    type: Array,
    default: () => [],
  },
})

const points = computed(() =>
  rows.value
    .map((row) => ({
      id: field(row, H.scriptId, 'play_id', 'script_id'),
      title: field(row, H.title, '\u5267\u672c\u540d\u79f0', 'title'),
      category: field(row, H.category, 'category') || '\u5176\u4ed6',
      weight: toNumber(field(row, H.weight, 'weight'), 0),
      nodeCount: toNumber(field(row, H.nodeCount, H.roleCount, '\u89d2\u8272\u603b\u6570', 'node_count'), 0),
      edgeCount: toNumber(field(row, H.edgeCount, '\u5b9e\u9645\u5173\u7cfb\u6570', 'edge_count'), 0),
      density: toNumber(field(row, H.density, 'density'), Number.NaN),
      centralization: toNumber(field(row, H.centralization, 'centralization'), Number.NaN),
      primaryRelation: field(row, H.primaryRelation),
      primaryTheme: field(row, H.primaryTheme),
    }))
    .filter(
      (row) =>
        row.id &&
        row.title &&
        Number.isFinite(row.density) &&
        Number.isFinite(row.centralization) &&
        row.density >= 0 &&
        row.centralization >= 0,
    ),
)

const categories = computed(() =>
  Array.from(new Set(points.value.map((point) => point.category))).sort((a, b) => a.localeCompare(b, 'zh-CN')),
)

const linkageByPlayId = computed(() => {
  const map = new Map()
  linkageRows.value.forEach((row) => {
    const playId = field(row, H.scriptId, 'play_id', 'script_id')
    if (!playId) return
    if (!map.has(playId)) map.set(playId, [])
    map.get(playId).push(row)
  })
  return map
})

const activeFilterLabel = computed(() => {
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return ''
  if (scope.type === 'relation') return scope.relationType
  if (scope.type === 'theme') return `${scope.relationType} / ${scope.themeCombo}`
  if (scope.type === 'flow' && flow) return `${flow.relationType} / ${flow.themeCombo} / ${flow.narrativeType}`
  return ''
})

onMounted(async () => {
  resizeObserver = new ResizeObserver((entries) => {
    const entry = entries[0]
    const nextWidth = Math.round(entry?.contentRect.width || 0)
    const nextHeight = Math.round(entry?.contentRect.height || 0)
    if (nextWidth === lastPanelWidth && nextHeight === lastPanelHeight) return
    lastPanelWidth = nextWidth
    lastPanelHeight = nextHeight
    scheduleDraw()
  })

  if (panelRef.value) resizeObserver.observe(panelRef.value)
  await loadRows()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (drawFrame) cancelAnimationFrame(drawFrame)
  d3.select(svgRef.value).selectAll('*').remove()
})

watch(points, async () => {
  await nextTick()
  scheduleDraw()
})

watch([activeFilterLabel, linkageByPlayId], async () => {
  await nextTick()
  updateScatterFilter()
})

async function loadRows() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [scatterResponse, linkageResponse] = await Promise.all([
      fetch(`${SCATTER_URL}?t=${Date.now()}`, { cache: 'no-store' }),
      fetch(`${LINKAGE_URL}?t=${Date.now()}`, { cache: 'no-store' }),
    ])
    if (!scatterResponse.ok) throw new Error(`读取散点数据失败：${scatterResponse.status}`)
    if (!linkageResponse.ok) throw new Error(`读取联动长表失败：${linkageResponse.status}`)

    const [scatterText, linkageText] = await Promise.all([scatterResponse.text(), linkageResponse.text()])
    rows.value = d3.csvParse(scatterText.replace(/^\uFEFF/, ''))
    linkageRows.value = d3.csvParse(linkageText.replace(/^\uFEFF/, ''))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function field(row, ...names) {
  for (const name of names) {
    const value = normalizeText(row[name])
    if (value) return value
  }
  return ''
}

function normalizeText(value) {
  return String(value ?? '').trim()
}

function toNumber(value, fallback = 0) {
  const numberValue = Number(String(value ?? '').replace(/,/g, '').trim())
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function pointMatchesFilter(point) {
  const scope = loopFilterState.scope
  if (!scope) return true
  const playRows = linkageByPlayId.value.get(point.id) || []
  return playRows.some((row) => loopRowMatchesScope(row, scope, loopFilterState.flow))
}

function loopRowMatchesScope(row, scope, flow) {
  const relation = field(row, H.relation)
  const theme = field(row, H.theme)
  const narrative = field(row, H.narrative)
  const wave = field(row, H.wave)
  const outcome = field(row, H.outcome)
  const flowId = field(row, H.flowId)

  if (scope.type === 'relation') return relation === scope.relationType
  if (scope.type === 'theme') return relation === scope.relationType && theme === scope.themeCombo

  if (scope.type === 'flow' && flow) {
    if (flowId && flow.id && flowId === flow.id) return true
    return (
      relation === flow.relationType &&
      theme === flow.themeCombo &&
      narrative === flow.narrativeType &&
      (!flow.waveType || wave === flow.waveType) &&
      outcome === flow.evolutionType
    )
  }

  return true
}

function drawChart() {
  const svgElement = svgRef.value
  const tooltipElement = tooltipRef.value
  if (!svgElement || !tooltipElement) return

  const chartWidth = width
  const chartHeight = getResponsiveHeight(svgElement)
  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${chartWidth} ${chartHeight}`).attr('preserveAspectRatio', 'xMidYMid meet')

  const renderPoints = points.value.slice().sort((a, b) => a.nodeCount - b.nodeCount)
  if (!renderPoints.length) return

  const plotWidth = chartWidth - margin.left - margin.right
  const plotHeight = chartHeight - margin.top - margin.bottom
  const x = d3.scaleLinear().domain([0, 1]).range([margin.left, margin.left + plotWidth])
  const y = d3.scaleLinear().domain([0, 1]).range([margin.top + plotHeight, margin.top])
  const weightExtent = d3.extent(renderPoints, (point) => point.weight || point.nodeCount)
  const weightDomain = weightExtent[0] === weightExtent[1] ? [0, weightExtent[1] || 1] : weightExtent
  const radius = d3.scaleSqrt().domain(weightDomain).range([4.5, 17])
  const xTicks = d3.range(0, 1.01, 0.2)
  const yTicks = d3.range(0, 1.01, 0.2)
  const paperFilterId = `${chartUid}-paper-grain`
  const plotClipId = `${chartUid}-plot-clip`

  const defs = svg.append('defs')
  const paperFilter = defs
    .append('filter')
    .attr('id', paperFilterId)
    .attr('x', '0')
    .attr('y', '0')
    .attr('width', '100%')
    .attr('height', '100%')

  paperFilter
    .append('feTurbulence')
    .attr('type', 'fractalNoise')
    .attr('baseFrequency', '0.85')
    .attr('numOctaves', 2)
    .attr('seed', 8)
    .attr('result', 'noise')

  paperFilter
    .append('feColorMatrix')
    .attr('in', 'noise')
    .attr('type', 'matrix')
    .attr('values', '0 0 0 0 0.55 0 0 0 0 0.36 0 0 0 0 0.18 0 0 0 .08 0')
    .attr('result', 'grain')

  paperFilter.append('feBlend').attr('in', 'SourceGraphic').attr('in2', 'grain').attr('mode', 'multiply')

  defs
    .append('clipPath')
    .attr('id', plotClipId)
    .append('rect')
    .attr('x', margin.left)
    .attr('y', margin.top)
    .attr('width', plotWidth)
    .attr('height', plotHeight)

  svg
    .append('rect')
    .attr('class', 'paper-background')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', chartWidth)
    .attr('height', chartHeight)
    .attr('filter', `url(#${paperFilterId})`)

  svg
    .append('rect')
    .attr('class', 'plot-background')
    .attr('x', margin.left)
    .attr('y', margin.top)
    .attr('width', plotWidth)
    .attr('height', plotHeight)

  const grid = svg.append('g').attr('class', 'grid-lines')
  grid
    .selectAll('line.vertical')
    .data(xTicks)
    .join('line')
    .attr('class', 'vertical')
    .attr('x1', (d) => x(d))
    .attr('x2', (d) => x(d))
    .attr('y1', margin.top)
    .attr('y2', margin.top + plotHeight)

  grid
    .selectAll('line.horizontal')
    .data(yTicks)
    .join('line')
    .attr('class', 'horizontal')
    .attr('x1', margin.left)
    .attr('x2', margin.left + plotWidth)
    .attr('y1', (d) => y(d))
    .attr('y2', (d) => y(d))

  const quadrantLines = svg.append('g').attr('class', 'quadrant-lines')
  quadrantLines
    .append('line')
    .attr('x1', x(0.5))
    .attr('x2', x(0.5))
    .attr('y1', margin.top)
    .attr('y2', margin.top + plotHeight)

  quadrantLines
    .append('line')
    .attr('x1', margin.left)
    .attr('x2', margin.left + plotWidth)
    .attr('y1', y(0.5))
    .attr('y2', y(0.5))

  const xAxis = d3.axisBottom(x).tickValues(xTicks).tickSize(5).tickPadding(9).tickFormat(formatTick)
  const yAxis = d3.axisLeft(y).tickValues(yTicks).tickSize(5).tickPadding(8).tickFormat(formatTick)

  svg
    .append('g')
    .attr('class', 'axis axis-x')
    .attr('transform', `translate(0,${margin.top + plotHeight})`)
    .call(xAxis)

  svg.append('g').attr('class', 'axis axis-y').attr('transform', `translate(${margin.left},0)`).call(yAxis)

  svg
    .append('text')
    .attr('class', 'axis-label axis-label-y')
    .attr('transform', `translate(${margin.left - 40},${margin.top + plotHeight / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .text('中心化')

  svg
    .append('text')
    .attr('class', 'axis-label axis-label-x')
    .attr('x', margin.left + plotWidth / 2)
    .attr('y', margin.top + plotHeight + 50)
    .attr('text-anchor', 'middle')
    .text('密度')

  svg.append('text').attr('class', 'filter-label').attr('x', margin.left).attr('y', margin.top + 24)

  const dotGroups = svg
    .append('g')
    .attr('class', 'dot-layer')
    .attr('clip-path', `url(#${plotClipId})`)
    .selectAll('g')
    .data(renderPoints, (d) => d.id)
    .join('g')
    .attr('class', 'scatter-dot is-matched')
    .attr('transform', (d) => `translate(${x(d.density)},${y(d.centralization)})`)
    .style('opacity', 1)
    .on('mouseenter', (event, d) => {
      if (!pointMatchesFilter(d)) return
      d3.select(event.currentTarget).raise().classed('is-active', true)
      showTooltip(event, d, tooltipElement)
    })
    .on('mousemove', (event, d) => {
      if (pointMatchesFilter(d)) showTooltip(event, d, tooltipElement)
    })
    .on('mouseleave', (event) => {
      d3.select(event.currentTarget).classed('is-active', false)
      hideTooltip(tooltipElement)
    })

  dotGroups
    .append('circle')
    .attr('class', 'scatter-circle')
    .attr('r', (d) => radius(d.weight || d.nodeCount))
    .attr('fill', (d) => getCategoryColor(d.category))

  drawLegend(svg, chartWidth, chartHeight)
  updateScatterFilter(false)
}

function updateScatterFilter(animate = true) {
  const svgElement = svgRef.value
  if (!svgElement) return

  const dots = d3.select(svgElement).selectAll('.scatter-dot')
  if (dots.empty()) return

  dots
    .interrupt()
    .classed('is-muted', (d) => !pointMatchesFilter(d))
    .classed('is-matched', (d) => pointMatchesFilter(d))
    .style('pointer-events', (d) => (pointMatchesFilter(d) ? 'auto' : 'none'))
    .transition()
    .duration(animate ? 900 : 0)
    .ease(d3.easeCubicOut)
    .style('opacity', (d) => (pointMatchesFilter(d) ? 1 : 0))

  d3.select(svgElement)
    .select('.filter-label')
    .text(activeFilterLabel.value ? `中上联动：${activeFilterLabel.value}` : '')
}

function returnToFullScatter() {
  clearLoopFilter()
  if (tooltipRef.value) hideTooltip(tooltipRef.value)
  updateScatterFilter()
}

function scheduleDraw() {
  if (drawFrame) cancelAnimationFrame(drawFrame)
  drawFrame = requestAnimationFrame(() => {
    drawFrame = 0
    drawChart()
  })
}

function getResponsiveHeight(svgElement) {
  const rect = svgElement.getBoundingClientRect()
  if (!rect.width || !rect.height) return height
  return Math.max(360, Math.round((width * rect.height) / rect.width))
}

function drawLegend(svg, chartWidth, chartHeight) {
  const legend = svg
    .append('g')
    .attr('class', 'legend')
    .attr('transform', `translate(${margin.left},${chartHeight - 46})`)

  const titleWidth = 104
  const rowGap = 28
  const itemsPerRow = Math.max(1, Math.ceil(categories.value.length / 2))
  const itemStep = Math.min(
    138,
    Math.max(104, (chartWidth - margin.left - margin.right - titleWidth) / itemsPerRow),
  )

  legend.append('text').attr('class', 'legend-title').attr('x', 0).attr('y', 6).text('剧目类别')

  categories.value.forEach((category, index) => {
    const row = Math.floor(index / itemsPerRow)
    const column = index % itemsPerRow
    const item = legend
      .append('g')
      .attr('transform', `translate(${titleWidth + column * itemStep},${row * rowGap})`)

    item.append('circle').attr('class', 'legend-dot').attr('r', 8).attr('fill', getCategoryColor(category))
    item.append('text').attr('x', 18).attr('y', 6).text(category)
  })
}

function getCategoryColor(category) {
  return categoryColors.get(category) || d3.schemeTableau10[categories.value.indexOf(category) % 10]
}

function formatTick(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function showTooltip(event, point, tooltipElement) {
  tooltipElement.innerHTML = `
    <b>${point.title}</b>
    <span>类别：${point.category}</span>
    <span>密度：${point.density.toFixed(4)}</span>
    <span>中心化：${point.centralization.toFixed(4)}</span>
    <span>内容量权重：${point.weight.toFixed(2)}</span>
    <span>角色：${point.nodeCount} 关系：${point.edgeCount}</span>
    <span>主关系：${point.primaryRelation || '未标注'}</span>
    <span>主主题：${point.primaryTheme || '未标注'}</span>
  `
  tooltipElement.style.left = `${event.offsetX + 14}px`
  tooltipElement.style.top = `${event.offsetY + 14}px`
  tooltipElement.classList.add('is-visible')
}

function hideTooltip(tooltipElement) {
  tooltipElement.classList.remove('is-visible')
}
</script>

<style scoped>
.scatter-panel {
  display: block;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 2px;
}

.scatter-chart {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.scatter-chart :deep(.paper-background) {
  fill: #fef9ed;
}

.scatter-chart :deep(.plot-background) {
  fill: #f7efde;
  stroke: rgba(143, 47, 36, 0.2);
  stroke-width: 1;
}

.scatter-chart :deep(.axis-label) {
  fill: #5e251d;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 24px;
  font-weight: 800;
}

.scatter-chart :deep(.filter-label) {
  fill: #8f2f24;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 18px;
  font-weight: 900;
  paint-order: stroke;
  stroke: rgba(255, 248, 232, 0.88);
  stroke-width: 4px;
}

.scatter-chart :deep(.grid-lines line) {
  stroke: #c7a87a;
  stroke-width: 1;
  stroke-dasharray: 2 7;
  opacity: 0.54;
}

.scatter-chart :deep(.quadrant-lines line) {
  stroke: #9f2f24;
  stroke-width: 1.1;
  stroke-dasharray: 6 5;
  opacity: 0.54;
}

.scatter-chart :deep(.axis path) {
  stroke: #8f2f24;
  stroke-width: 1.4;
}

.scatter-chart :deep(.axis line) {
  stroke: #8f2f24;
  stroke-width: 1.2;
}

.scatter-chart :deep(.axis text) {
  fill: #4b3328;
  font-family: 'Times New Roman', 'Microsoft YaHei', serif;
  font-size: 18px;
  font-weight: 700;
}

.scatter-chart :deep(.scatter-dot) {
  cursor: pointer;
}

.scatter-chart :deep(.scatter-dot.is-muted) {
  pointer-events: none;
}

.scatter-chart :deep(.scatter-circle) {
  fill-opacity: 0.72;
  transition: fill-opacity 0.15s ease;
}

.scatter-chart :deep(.scatter-dot.is-active .scatter-circle) {
  fill-opacity: 0.94;
}

.scatter-chart :deep(.legend text) {
  fill: #4b3328;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 19px;
  font-weight: 800;
}

.scatter-chart :deep(.legend-title) {
  fill: #8f2f24;
  font-size: 21px;
  font-weight: 800;
}

.scatter-chart :deep(.legend-dot) {
  fill-opacity: 0.84;
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6b4d35;
  background: rgba(244, 234, 214, 0.72);
  font-size: 13px;
  pointer-events: none;
}

.chart-state--error {
  color: #9b2f2a;
}

.scatter-return-btn {
  position: absolute;
  right: 18px;
  bottom: 56px;
  z-index: 4;
  min-width: 82px;
  height: 28px;
  padding: 0 12px;
  border: 1px solid rgba(143, 47, 36, 0.36);
  border-radius: 999px;
  color: #fff8ed;
  background: linear-gradient(135deg, #8f2f24, #3d1d17);
  box-shadow: 0 10px 22px rgba(82, 31, 18, 0.22);
  cursor: pointer;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 13px;
  font-weight: 900;
  line-height: 26px;
}

.scatter-return-btn:hover {
  filter: brightness(1.08) saturate(1.18);
}

.scatter-tooltip {
  position: absolute;
  z-index: 3;
  display: grid;
  gap: 3px;
  max-width: 230px;
  padding: 8px 10px;
  border: 1px solid rgba(143, 47, 36, 0.32);
  border-radius: 6px;
  color: #3f2c20;
  background: rgba(248, 238, 216, 0.97);
  box-shadow: 0 10px 24px rgba(88, 45, 28, 0.2);
  font-family: 'Microsoft YaHei', sans-serif;
  font-size: 13px;
  line-height: 1.45;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}

.scatter-tooltip b {
  color: #8f2f24;
  font-weight: 800;
}

.scatter-tooltip span {
  overflow-wrap: anywhere;
}

.scatter-tooltip.is-visible {
  opacity: 1;
  transform: translateY(0);
}
</style>
