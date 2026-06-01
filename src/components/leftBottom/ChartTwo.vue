<template>
  <div class="scatter-panel">
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
const height = 600
const margin = {
  top: 10,
  right: 34,
  bottom: 56,
  left: 42,
}

const categoryColors = new Map([
  ['历史戏', '#5c78d1'],
  ['战争戏', '#5c78d1'],
  ['公案戏', '#8ccb6f'],
  ['综合戏', '#f5bd47'],
  ['家庭戏', '#ee6b67'],
  ['伦理戏', '#ee6b67'],
  ['神话戏', '#78bfd2'],
])

const svgRef = ref(null)
const tooltipRef = ref(null)
const rows = ref([])
const loading = ref(false)
const errorMessage = ref('')

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
  await loadRows()
})

onBeforeUnmount(() => {
  d3.select(svgRef.value).selectAll('*').remove()
})

watch(points, async () => {
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

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${width} ${height}`)

  if (!points.value.length) return

  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom
  const x = d3.scaleLinear().domain([0, 1]).range([margin.left, margin.left + plotWidth])
  const y = d3.scaleLinear().domain([0, 1]).range([margin.top + plotHeight, margin.top])
  const radius = d3
    .scaleSqrt()
    .domain(d3.extent(points.value, (point) => point.nodeCount))
    .range([10, 40])

  const xTicks = d3.range(0, 1.01, 0.2)
  const yTicks = d3.range(0, 1.01, 0.2)



  svg
    .append('text')
    .attr('class', 'chart-caption')
    .attr('x', width - 8)
    .attr('y', -8)
    .attr('text-anchor', 'end')
    .text('每个点是一部剧：密度 × 中心化')

  svg
    .append('text')
    .attr('class', 'axis-label-y')
    .attr('x', margin.left - 18)
    .attr('y', margin.top - 17)
    .text('中心化')

  svg
    .append('text')
    .attr('class', 'axis-label-x')
    .attr('x', margin.left + plotWidth)
    .attr('y', margin.top + plotHeight + 36)
    .attr('text-anchor', 'end')
    .text('密度')

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

  const xAxis = d3.axisBottom(x).tickValues(xTicks).tickSize(0).tickFormat(formatTick)
  const yAxis = d3.axisLeft(y).tickValues(yTicks).tickSize(0).tickFormat(formatTick)

  svg
    .append('g')
    .attr('class', 'axis axis-x')
    .attr('transform', `translate(0,${margin.top + plotHeight})`)
    .call(xAxis)

  svg.append('g').attr('class', 'axis axis-y').attr('transform', `translate(${margin.left},0)`).call(yAxis)

  const dots = svg
    .append('g')
    .attr('class', 'dot-layer')
    .selectAll('circle')
    .data(points.value)
    .join('circle')
    .attr('cx', (d) => x(d.density))
    .attr('cy', (d) => y(d.betweenness))
    .attr('r', (d) => radius(d.nodeCount))
    .attr('fill', (d) => getCategoryColor(d.category))
    .attr('fill-opacity', 0.82)
    .on('mouseenter', (event, d) => {
      d3.select(event.currentTarget).attr('stroke-width', 2.4).attr('fill-opacity', 0.95)
      showTooltip(event, d, tooltipElement)
    })
    .on('mousemove', (event, d) => showTooltip(event, d, tooltipElement))
    .on('mouseleave', (event) => {
      d3.select(event.currentTarget).attr('stroke-width', 1.2).attr('fill-opacity', 0.82)
      hideTooltip(tooltipElement)
    })

  dots.attr('stroke', '#ffffff').attr('stroke-width', 1.2)

  drawLegend(svg)
}

function drawLegend(svg) {
  const legend = svg
    .append('g')
    .attr('class', 'legend')
    .attr('transform', `translate(${margin.left + 20},${height - 6})`)

  // 每个图例之间的横向间距
  const itemGapX = 135

  // 两行之间的上下间距
  const itemGapY = 34

  // 每行最多放几个
  const maxPerRow = Math.ceil(categories.value.length / 2)

  categories.value.forEach((category, index) => {
    const col = index % maxPerRow
    const row = Math.floor(index / maxPerRow)

    const item = legend
      .append('g')
      .attr('transform', `translate(${col * itemGapX},${row * itemGapY})`)

    item
      .append('circle')
      .attr('r', 12)
      .attr('cx', 0)
      .attr('cy', 0)
      .attr('fill', getCategoryColor(category))

    item
      .append('text')
      .attr('x', 26)
      .attr('y', 7)
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
    <span>种类：${point.category}</span>
    <span>角色数量：${point.nodeCount}</span>
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
  width: 100%;
  height: 100%;
  min-height: 0;
}

.scatter-chart {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 0;
}



.scatter-chart :deep(.chart-caption) {
  fill: #64748b;
  font-size: 16px;
  font-weight: 700;
}

.scatter-chart :deep(.axis-label-y),
.scatter-chart :deep(.axis-label-x) {
  fill: #64748b;
  font-size: 20px;
  font-weight: 800;
}

.scatter-chart :deep(.grid-lines line) {
  stroke: #dbe5f1;
  stroke-width: 1;
}

.scatter-chart :deep(.axis path) {
  stroke: #7b8492;
  stroke-width: 1.4;
}

.scatter-chart :deep(.axis text) {
  fill: #5f6673;
  font-size: 20px;
  font-weight: 700;
}

.scatter-chart :deep(.axis .tick line) {
  display: none;
}

.scatter-chart :deep(.dot-layer circle) {
  cursor: pointer;
  transition:
    fill-opacity 0.15s ease,
    stroke-width 0.15s ease;
}

.scatter-chart :deep(.legend text) {
  fill: #3f4652;
  font-size: 20px;
  font-weight: 600;
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #64748b;
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
  border: 1px solid rgba(47, 58, 76, 0.16);
  border-radius: 6px;
  color: #273142;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 22px rgba(30, 41, 59, 0.18);
  font-size: 12px;
  line-height: 1.45;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}

.scatter-tooltip b {
  color: #1e293b;
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
