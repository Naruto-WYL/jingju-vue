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
import { loopFilterState } from '../../services/loopFilterStore'

const DATA_URL = '/数据表合集/2/京剧剧本_网络指标总表_已补核心字段_过滤密度中心度1.csv'
const width = 760
const height = 700
const margin = {
  top: 12,
  right: 20,
  bottom: 120,
  left: 80,
}

const chartUid = `script-scatter-${Math.random().toString(36).slice(2, 10)}`
const paperInset = 0

const categoryColors = new Map([
  ['历史戏', '#d84f5d'],
  ['家庭戏', '#e68a57'],
  ['神怪戏', '#36a8b6'],
  ['公案戏', '#d0a53c'],
  ['江湖戏', '#5f82c8'],
  ['战争戏', '#aa72c8'],
  ['综合戏', '#b78263'],
])

const svgRef = ref(null)
const panelRef = ref(null)
const tooltipRef = ref(null)
const rows = ref([])
const loading = ref(false)
const errorMessage = ref('')
const localFilterDismissed = ref(false)
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
      id: normalizeText(row['剧本ID']),
      title: normalizeText(row['剧本名称']),
      category: normalizeText(row['剧目类别']) || '其他',
      nodeCount: toNumber(row['角色总数'], 0),
      edgeCount: toNumber(row['实际关系数'], 0),
      density: toNumber(row['网络密度'], Number.NaN),
      centralization: toNumber(row['度中心化'], Number.NaN),
      coreRelation: normalizeText(row['核心关系']),
      coreTheme: normalizeText(row['核心主题']),
    }))
    .filter(
      (row) =>
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

const activeFilterLabel = computed(() => {
  if (localFilterDismissed.value) return ''
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return ''
  if (scope.type === 'relation') return scope.relationType
  if (scope.type === 'theme') return `${scope.relationType} / ${scope.themeCombo}`
  if (scope.type === 'flow' && flow) return `${flow.relationType} / ${flow.themeCombo}`
  return ''
})

watch(
  () => [loopFilterState.scope, loopFilterState.flow],
  () => {
    localFilterDismissed.value = false
  },
)

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

watch(activeFilterLabel, async () => {
  await nextTick()
  updateScatterFilter()
})

async function loadRows() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(encodeURI(`${DATA_URL}?t=${Date.now()}`), { cache: 'no-store' })
    if (!response.ok) throw new Error(`读取失败：${response.status}`)

    const text = await response.text()
    rows.value = d3.csvParse(text.replace(/^\uFEFF/, ''))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function normalizeText(value) {
  return String(value ?? '').trim()
}

function toNumber(value, fallback = 0) {
  const numberValue = Number(String(value ?? '').replace(/,/g, '').trim())
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function pointMatchesFilter(point) {
  if (localFilterDismissed.value) return true
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return true

  if (scope.type === 'relation') {
    return point.coreRelation === scope.relationType
  }

  if (scope.type === 'theme') {
    return point.coreRelation === scope.relationType && point.coreTheme === scope.themeCombo
  }

  if (scope.type === 'flow' && flow) {
    return point.coreRelation === flow.relationType && point.coreTheme === flow.themeCombo
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
  const nodeExtent = d3.extent(renderPoints, (point) => point.nodeCount)
  const nodeDomain = nodeExtent[0] === nodeExtent[1] ? [0, nodeExtent[1] || 1] : nodeExtent
  const radius = d3.scaleSqrt().domain(nodeDomain).range([4.5, 17])
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
    .attr('r', (d) => radius(d.nodeCount))
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
    .style('opacity', (d) => (pointMatchesFilter(d) ? 1 : 0.06))

  d3.select(svgElement)
    .select('.filter-label')
    .text(activeFilterLabel.value ? `中上联动：${activeFilterLabel.value}` : '')
}

function returnToFullScatter() {
  localFilterDismissed.value = true
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
    .attr('transform', `translate(${margin.left},${chartHeight - 38})`)

  const titleWidth = 88
  const itemsPerRow = Math.max(1, categories.value.length)
  const itemStep = (chartWidth - margin.left - margin.right - titleWidth) / itemsPerRow

  legend.append('text').attr('class', 'legend-title').attr('x', 0).attr('y', 6).text('剧目类别')

  categories.value.forEach((category, index) => {
    const item = legend
      .append('g')
      .attr('transform', `translate(${titleWidth + index * itemStep},0)`)

    item.append('circle').attr('class', 'legend-dot').attr('r', 8).attr('fill', getCategoryColor(category))

    item
      .append('text')
      .attr('x', 18)
      .attr('y', 6)
      .text(category)
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
    <span>角色：${point.nodeCount} 关系：${point.edgeCount}</span>
    <span>核心关系：${point.coreRelation || '未标注'}</span>
    <span>核心主题：${point.coreTheme || '未标注'}</span>
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
  background: #FBF6E9;
}

.scatter-chart {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.scatter-chart :deep(.paper-background) {
  fill: #FBF6E9;
}

.scatter-chart :deep(.plot-background) {
  fill: #FBF6E9;
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
  top: 12px;
  right: 14px;
  z-index: 4;
  min-width: 0;
  height: 26px;
  padding: 0 12px;
  border: 1px solid rgba(143, 47, 36, 0.46);
  border-radius: 6px;
  color: #7a241d;
  background: rgba(255, 249, 237, 0.92);
  box-shadow: 0 4px 10px rgba(80, 35, 12, 0.12);
  cursor: pointer;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  font-size: 12px;
  font-weight: 800;
  line-height: 24px;
}

.scatter-return-btn:hover {
  border-color: rgba(143, 47, 36, 0.72);
  background: #fff4dc;
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
