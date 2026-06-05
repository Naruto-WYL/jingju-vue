<template>
  <div ref="panelRef" class="scatter-panel">
    <svg ref="svgRef" class="scatter-chart" role="img" aria-label="网络结构散点图" />

    <div v-if="loading" class="chart-state">数据加载中...</div>
    <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
    <div v-else-if="!points.length" class="chart-state">暂无散点数据</div>

    <div ref="tooltipRef" class="scatter-tooltip" />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import * as XLSX from 'xlsx'

const DATA_URL = '/数据表合集/2/p2_script_metrics.xlsx'
const width = 760
const height = 700
const margin = {
  top: 58,
  right: 54,
  bottom: 92,
  left: 50,
}

const chartUid = `script-scatter-${Math.random().toString(36).slice(2, 10)}`
const paperInset = 0
const plaqueLabelFontSize = 20
const plaqueLabelPadding = 5

const categoryColors = new Map([
  ['历史戏', '#b0181f'],
  ['战争戏', '#1f4f99'],
  ['公案戏', '#0f7b68'],
  ['综合戏', '#c58a12'],
  ['家庭戏', '#b13f75'],
  ['伦理戏', '#6f3d9f'],
  ['神话戏', '#188a9a'],
])

const svgRef = ref(null)
const panelRef = ref(null)
const tooltipRef = ref(null)
const rows = ref([])
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
      title: normalizeText(row.script_title),
      category: normalizeText(row.category) || '其他',
      nodeCount: Number(row.node_count) || 0,
      density: Number(row.density),
      betweenness: Number(row.betweenness),
    }))
    .filter((row) => row.title && Number.isFinite(row.density) && Number.isFinite(row.betweenness)),
)

const categories = computed(() => Array.from(new Set(points.value.map((point) => point.category))))

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

  if (panelRef.value) {
    resizeObserver.observe(panelRef.value)
  }

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

async function loadRows() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(encodeURI(DATA_URL))
    if (!response.ok) throw new Error(`读取失败：${response.status}`)

    const buffer = await response.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    rows.value = XLSX.utils.sheet_to_json(sheet, { defval: '' })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function normalizeText(value) {
  return String(value ?? '').trim()
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

  if (!points.value.length) return

  const plotWidth = chartWidth - margin.left - margin.right
  const plotHeight = chartHeight - margin.top - margin.bottom
  const x = d3.scaleLinear().domain([0, 1]).range([margin.left, margin.left + plotWidth])
  const y = d3.scaleLinear().domain([0, 1]).range([margin.top + plotHeight, margin.top])
  const plaqueWidth = d3
  .scaleSqrt()
  .domain(d3.extent(points.value, (point) => point.nodeCount))
  .range([44, 115])

const plaqueHeight = d3
  .scaleSqrt()
  .domain(plaqueWidth.domain())
  .range([24, 42])

  const xTicks = d3.range(0, 1.01, 0.2)
  const yTicks = d3.range(0, 1.01, 0.2)
  const paperFilterId = `${chartUid}-paper-grain`
  const plotClipId = `${chartUid}-plot-clip`
  const renderPoints = points.value.slice().sort((a, b) => a.nodeCount - b.nodeCount)

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
    .attr('x', paperInset)
    .attr('y', paperInset)
    .attr('width', chartWidth - paperInset * 2)
    .attr('height', chartHeight - paperInset * 2)
    .attr('filter', `url(#${paperFilterId})`)

  svg
    .append('rect')
    .attr('class', 'plot-background')
    .attr('x', margin.left)
    .attr('y', margin.top)
    .attr('width', plotWidth)
    .attr('height', plotHeight)

  svg
    .append('text')
    .attr('class', 'chart-caption')
    .attr('x', margin.left)
    .attr('y', 36)
    .text('剧目网络结构分布')

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
    .attr('transform', `translate(${margin.left - 26},${margin.top + plotHeight / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .text('中心化')

  svg
    .append('text')
    .attr('class', 'axis-label axis-label-x')
    .attr('x', margin.left + plotWidth / 2)
    .attr('y', margin.top + plotHeight + 48)
    .attr('text-anchor', 'middle')
    .text('密度')

  const dotGroups = svg
    .append('g')
    .attr('class', 'dot-layer')
    .attr('clip-path', `url(#${plotClipId})`)
    .selectAll('g')
    .data(renderPoints)
    .join('g')
    .attr('class', 'scatter-dot')
    .attr('transform', (d) => `translate(${x(d.density)},${y(d.betweenness)})`)
    .on('mouseenter', (event, d) => {
      d3.select(event.currentTarget).raise().classed('is-active', true)
      showTooltip(event, d, tooltipElement)
    })
    .on('mousemove', (event, d) => showTooltip(event, d, tooltipElement))
    .on('mouseleave', (event) => {
      d3.select(event.currentTarget).classed('is-active', false)
      hideTooltip(tooltipElement)
    })

  dotGroups
    .append('path')
    .attr('class', 'plaque-back')
    .attr('d', (d) => createPlaquePath(plaqueWidth(d.nodeCount), plaqueHeight(d.nodeCount)))
    .attr('fill', (d) => getCategoryColor(d.category))

  dotGroups
    .append('path')
    .attr('class', 'plaque-face')
    .attr('d', (d) => createPlaquePath(plaqueWidth(d.nodeCount), plaqueHeight(d.nodeCount)))
    .attr('fill', (d) => getCategoryColor(d.category))

  dotGroups
    .append('path')
    .attr('class', 'plaque-inner')
    .attr('d', (d) =>
      createPlaquePath(Math.max(28, plaqueWidth(d.nodeCount) - 10), Math.max(14, plaqueHeight(d.nodeCount) - 8), 4),
    )

  dotGroups
    .filter((d) => shouldShowPlaqueLabel(d, plaqueWidth(d.nodeCount), plaqueHeight(d.nodeCount)))
    .append('text')
    .attr('class', 'plaque-text')
    .attr('y', 7)
    .attr('text-anchor', 'middle')
    .text((d) => d.title)

  drawLegend(svg, chartWidth, chartHeight)
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
    .attr('transform', `translate(${margin.left},${chartHeight - 28})`)

  const titleWidth = 86
  const itemStep = Math.min(
    108,
    Math.max(78, (chartWidth - margin.left - margin.right - titleWidth) / Math.max(1, categories.value.length)),
  )

  legend.append('text').attr('class', 'legend-title').attr('x', 0).attr('y', 6).text('戏剧种类')

  categories.value.forEach((category, index) => {
    const item = legend
      .append('g')
      .attr('transform', `translate(${titleWidth + index * itemStep},0)`)

    item
      .append('path')
      .attr('class', 'legend-plaque')
      .attr('d', createPlaquePath(34, 18, 3))
      .attr('fill', getCategoryColor(category))

    item.append('path').attr('class', 'legend-plaque-inner').attr('d', createPlaquePath(26, 12, 2))

    item
      .append('text')
      .attr('x', 26)
      .attr('y', 5)
      .text(category)
  })
}

function createPlaquePath(widthValue, heightValue, stepValue = 5) {
  const w = Math.max(18, widthValue)
  const h = Math.max(10, heightValue)
  const s = Math.min(stepValue, w / 8, h / 4)
  const x = -w / 2
  const y = -h / 2

  return [
    `M${x + s * 2},${y}`,
    `L${x + w - s * 2},${y}`,
    `L${x + w - s * 2},${y + s}`,
    `L${x + w - s},${y + s}`,
    `L${x + w - s},${y + s * 2}`,
    `L${x + w},${y + s * 2}`,
    `L${x + w},${y + h - s * 2}`,
    `L${x + w - s},${y + h - s * 2}`,
    `L${x + w - s},${y + h - s}`,
    `L${x + w - s * 2},${y + h - s}`,
    `L${x + w - s * 2},${y + h}`,
    `L${x + s * 2},${y + h}`,
    `L${x + s * 2},${y + h - s}`,
    `L${x + s},${y + h - s}`,
    `L${x + s},${y + h - s * 2}`,
    `L${x},${y + h - s * 2}`,
    `L${x},${y + s * 2}`,
    `L${x + s},${y + s * 2}`,
    `L${x + s},${y + s}`,
    `L${x + s * 2},${y + s}`,
    'Z',
  ].join('')
}

function shouldShowPlaqueLabel(point, widthValue, heightValue) {
  return heightValue >= 34 && estimateTextWidth(point.title) <= widthValue - plaqueLabelPadding
}

function estimateTextWidth(value) {
  return Array.from(value).reduce((widthSum, char) => {
    if (/[\u4e00-\u9fff]/.test(char)) return widthSum + plaqueLabelFontSize
    if (/[·，、。；：]/.test(char)) return widthSum + plaqueLabelFontSize * 0.55
    return widthSum + plaqueLabelFontSize * 0.62
  }, 0)
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
    <span>种类：${point.category}</span>
    <span>密度：${point.density.toFixed(4)}</span>
    <span>中心化：${point.betweenness.toFixed(4)}</span>
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
  border: 1px solid rgba(143, 47, 36, 0.16);
  border-radius: 2px;
  background:
    linear-gradient(135deg, rgba(185, 72, 52, 0.13), rgba(244, 234, 214, 0.12) 46%, rgba(47, 127, 109, 0.09)),
    #df9707;
}

.scatter-chart {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.scatter-chart :deep(.paper-background) {
  fill: #fde5b5;
  stroke: rgba(143, 47, 36, 0.2);
  stroke-width: 1.1;
}

.scatter-chart :deep(.plot-background) {
  fill: rgba(255, 249, 233, 0.5);
  stroke: rgba(143, 47, 36, 0.2);
  stroke-width: 1;
}

.scatter-chart :deep(.chart-caption) {
  fill: #8f2f24;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 26px;
  font-weight: 800;
}

.scatter-chart :deep(.axis-label) {
  fill: #5e251d;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 24px;
  font-weight: 800;
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
  opacity: 0.56;
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

.scatter-chart :deep(.plaque-back) {
  stroke: rgba(84, 45, 28, 0.78);
  stroke-linejoin: round;
  stroke-width: 1.4;
}

.scatter-chart :deep(.plaque-face) {
  stroke: #f5ddb0;
  stroke-linejoin: round;
  stroke-width: 4;
  transition:
    opacity 0.15s ease,
    stroke-width 0.15s ease;
}

.scatter-chart :deep(.plaque-inner) {
  fill: none;
  stroke: rgba(255, 247, 218, 0.9);
  stroke-linejoin: round;
  stroke-width: 1.5;
  pointer-events: none;
}

.scatter-chart :deep(.scatter-dot.is-active .plaque-face) {
  opacity: 0.92;
  stroke-width: 5;
}

.scatter-chart :deep(.plaque-text) {
  fill: #fff6d7;
  stroke: rgba(83, 38, 24, 0.58);
  stroke-linejoin: round;
  stroke-width: 2.5px;
  paint-order: stroke;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 20px;
  font-weight: 800;
  pointer-events: none;
}

.scatter-chart :deep(.legend text) {
  fill: #4b3328;
  font-family: 'STKaiti', 'KaiTi', 'Microsoft YaHei', sans-serif;
  font-size: 17px;
  font-weight: 700;
}

.scatter-chart :deep(.legend-title) {
  fill: #8f2f24;
  font-size: 18px;
  font-weight: 800;
}

.scatter-chart :deep(.legend-plaque) {
  stroke: #f5ddb0;
  stroke-linejoin: round;
  stroke-width: 2.4;
}

.scatter-chart :deep(.legend-plaque-inner) {
  fill: none;
  stroke: rgba(255, 247, 218, 0.9);
  stroke-linejoin: round;
  stroke-width: 1;
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

.scatter-tooltip {
  position: absolute;
  z-index: 3;
  display: grid;
  gap: 3px;
  max-width: 220px;
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
