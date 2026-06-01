<template>
  <div class="trade-pattern-panel">
    <div class="role-selector">
      <label class="selector-field">
        <span>剧目</span>
        <select v-model="selectedScript">
          <option v-for="script in scripts" :key="script" :value="script">{{ script }}</option>
        </select>
      </label>

      <div class="period-field">
        <span>时期</span>
        <strong>{{ currentPeriod || '暂无' }}</strong>
      </div>

      <label class="selector-field">
        <span>角色</span>
        <select v-model="selectedRole">
          <option v-for="role in roles" :key="role" :value="role">{{ role }}</option>
        </select>
      </label>

      <div class="trade-badge" :class="{ 'is-inferred': isInferredTrade, 'is-known': isKnownTrade }">
        <span>行当</span>
        <strong>{{ currentTrade || '暂无' }}</strong>
      </div>
    </div>

    <div class="heatmap-wrap">
      <svg ref="svgRef" class="trade-heatmap" role="img" aria-label="行当特征热力图" />
      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
      <div v-else-if="!heatmapRows.length" class="chart-state">暂无热力图数据</div>
      <div ref="tooltipRef" class="heatmap-tooltip" />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'

const ROLE_URL = '/数据表合集/1/Table1_Role_Inference.csv'
const HEATMAP_URL = '/数据表合集/1/Table2_Trade_Vector_Patterns.csv'
const width = 680
const height = 430
const margin = {
  top: 24,
  right: 16,
  bottom: 52,
  left: 50,
}

const metricLabels = {
  score_zhongyi: '忠义',
  score_zhimou: '智谋',
  score_yongwu: '勇武',
  score_jiaozha: '狡诈',
  score_baozao: '暴躁',
  appear_ratio: '出场',
  sing_ratio: '唱段',
  fight_ratio: '打斗',
  cry_ratio: '哭',
  laugh_ratio: '笑',
  sample_count: '样本数',
}
const heatmapColors = ['#f8efe2', '#efd2aa', '#d98a52', '#b83b31', '#6f1418']

const svgRef = ref(null)
const tooltipRef = ref(null)
const roleRows = ref([])
const heatmapRows = ref([])
const selectedScript = ref('')
const selectedRole = ref('')
const loading = ref(false)
const errorMessage = ref('')

defineProps({
  stats: {
    type: Object,
    default: () => ({}),
  },
})

const scripts = computed(() => unique(roleRows.value.map((row) => row.script_name)).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN')))

const currentScriptRows = computed(() => roleRows.value.filter((row) => row.script_name === selectedScript.value))

const roles = computed(() =>
  unique(currentScriptRows.value.map((row) => row.role_name)).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN')),
)

const selectedRoleRow = computed(
  () => currentScriptRows.value.find((row) => row.role_name === selectedRole.value) || currentScriptRows.value[0] || null,
)

const currentPeriod = computed(() => selectedRoleRow.value?.historical_period || currentScriptRows.value[0]?.historical_period || '')
const currentTrade = computed(() => selectedRoleRow.value?.trade || '')
const isInferredTrade = computed(() => currentTrade.value.includes('推断'))
const isKnownTrade = computed(() => currentTrade.value.includes('已知'))

const tradeNames = computed(() => heatmapRows.value.map((row) => row.clean_trade).filter(Boolean))

const metrics = computed(() => {
  const firstRow = heatmapRows.value[0]
  if (!firstRow) return []
  return Object.keys(firstRow).filter((key) => key !== 'clean_trade')
})

const cells = computed(() =>
  heatmapRows.value.flatMap((row) =>
    metrics.value.map((metric) => ({
      trade: row.clean_trade,
      metric,
      label: metricLabels[metric] || metric,
      value: Number(row[metric]) || 0,
    })),
  ),
)

onMounted(async () => {
  await loadData()
})

onBeforeUnmount(() => {
  d3.select(svgRef.value).selectAll('*').remove()
})

watch(scripts, (nextScripts) => {
  if (!selectedScript.value && nextScripts.length) selectedScript.value = nextScripts[0]
})

watch(roles, (nextRoles) => {
  if (!nextRoles.includes(selectedRole.value)) {
    selectedRole.value = nextRoles[0] || ''
  }
})

watch(cells, async () => {
  await nextTick()
  drawHeatmap()
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [roleData, heatmapData] = await Promise.all([
      d3.csv(encodeURI(ROLE_URL), normalizeRoleRow),
      d3.csv(encodeURI(HEATMAP_URL), normalizeHeatmapRow),
    ])
    roleRows.value = roleData
    heatmapRows.value = heatmapData
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function normalizeRoleRow(row) {
  return {
    script_name: text(row.script_name),
    historical_period: text(row.historical_period),
    role_name: text(row.role_name),
    trade: text(row.trade),
  }
}

function normalizeHeatmapRow(row) {
  return Object.fromEntries(Object.entries(row).map(([key, value]) => [key, key === 'clean_trade' ? text(value) : Number(value) || 0]))
}

function drawHeatmap() {
  const svgElement = svgRef.value
  const tooltipElement = tooltipRef.value
  if (!svgElement || !tooltipElement) return

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${width} ${height}`)

  if (!cells.value.length) return

  const plotWidth = width - margin.left - margin.right
  const plotHeight = height - margin.top - margin.bottom
  const x = d3.scaleBand().domain(metrics.value).range([margin.left, margin.left + plotWidth]).padding(0.08)
  const y = d3
    .scaleBand()
    .domain(tradeNames.value)
    .range([margin.top, margin.top + plotHeight])
    .padding(0.035)
  const maxValue = d3.max(cells.value, (cell) => cell.value) || 1
  const color = d3.scaleLinear().domain(d3.range(0, 1.01, 0.25).map((step) => step * maxValue)).range(heatmapColors)

  svg
    .append('text')
    .attr('class', 'heatmap-title')
    .attr('x', margin.left - 4)
    .attr('y', 15)
    .text('行当特征向量热力图')

  svg
  .append('g')
  .attr('class', 'axis axis-x')
  .attr('transform', `translate(0,${margin.top + plotHeight + 4})`)
  .call(
    d3
      .axisBottom(x)
      .tickSize(0)
      .tickPadding(8)
      .tickFormat((metric) => metricLabels[metric] || metric),
  )
  .selectAll('text')
  .attr('transform', null)
  .attr('text-anchor', 'middle')
  .attr('dx', '0')
  .attr('dy', '0.9em')

  svg
    .append('g')
    .attr('class', 'axis axis-y')
    .attr('transform', `translate(${margin.left},0)`)
    .call(d3.axisLeft(y).tickSize(0))

  svg
    .append('g')
    .attr('class', 'heatmap-cells')
    .selectAll('rect')
    .data(cells.value)
    .join('rect')
    .attr('x', (d) => x(d.metric))
    .attr('y', (d) => y(d.trade))
    .attr('width', x.bandwidth())
    .attr('height', y.bandwidth())
    .attr('rx', 2)
    .attr('fill', (d) => color(d.value))
    .on('mouseenter', (event, d) => {
      d3.select(event.currentTarget).attr('stroke', '#6f1418').attr('stroke-width', 1.6)
      showTooltip(event, d, tooltipElement)
    })
    .on('mousemove', (event, d) => showTooltip(event, d, tooltipElement))
    .on('mouseleave', (event) => {
      d3.select(event.currentTarget).attr('stroke', 'rgba(255,255,255,0.78)').attr('stroke-width', 1)
      hideTooltip(tooltipElement)
    })
    .attr('stroke', null)
    .attr('stroke-width', 0)

  drawColorLegend(svg, color, maxValue)
}

function drawColorLegend(svg, color, maxValue) {
  const legendWidth = 120
  const legendHeight = 7
  const legendX = width - margin.right - legendWidth
  const legendY = 10
  const gradientId = 'tradeHeatmapGradient'

  const defs = svg.append('defs')
  const gradient = defs
    .append('linearGradient')
    .attr('id', gradientId)
    .attr('x1', '0%')
    .attr('x2', '100%')
    .attr('y1', '0%')
    .attr('y2', '0%')

  d3.range(0, 1.01, 0.2).forEach((step) => {
    gradient
      .append('stop')
      .attr('offset', `${step * 100}%`)
      .attr('stop-color', color(step * maxValue))
  })

  svg
    .append('rect')
    .attr('class', 'heatmap-legend')
    .attr('x', legendX)
    .attr('y', legendY)
    .attr('width', legendWidth)
    .attr('height', legendHeight)
    .attr('fill', `url(#${gradientId})`)

  svg.append('text').attr('class', 'legend-text').attr('x', legendX).attr('y', legendY + 19).text('低')
  svg
    .append('text')
    .attr('class', 'legend-text')
    .attr('x', legendX + legendWidth)
    .attr('y', legendY + 19)
    .attr('text-anchor', 'end')
    .text('高')
}

function showTooltip(event, cell, tooltipElement) {
  tooltipElement.innerHTML = `
    <b>${cell.trade}</b>
    <span>指标：${cell.label}</span>
    <span>数值：${cell.value.toFixed(4)}</span>
  `
  tooltipElement.style.left = `${event.offsetX + 14}px`
  tooltipElement.style.top = `${event.offsetY + 14}px`
  tooltipElement.classList.add('is-visible')
}

function hideTooltip(tooltipElement) {
  tooltipElement.classList.remove('is-visible')
}

function unique(values) {
  return Array.from(new Set(values.map(text).filter(Boolean)))
}

function text(value) {
  return String(value ?? '').trim()
}
</script>

<style scoped>
.trade-pattern-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
  height: 100%;
  min-height: 0;
}

.role-selector {
  display: grid;
  grid-template-columns: minmax(110px, 1.5fr) minmax(72px, 0.8fr) minmax(100px, 1.1fr) minmax(88px, 0.9fr);
  gap: 7px;
  align-items: end;
  min-height: 38px;
}

.selector-field,
.period-field,
.trade-badge {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.selector-field span,
.period-field span,
.trade-badge span {
  color: #6b5b4d;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.selector-field select,
.period-field strong,
.trade-badge strong {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 25px;
  padding: 0 8px;
  border: 1px solid rgba(111, 20, 24, 0.16);
  border-radius: 5px;
  color: #352d27;
  background: rgba(255, 252, 244, 0.78);
  font-size: 11px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selector-field select {
  outline: none;
}

.selector-field select:focus {
  border-color: rgba(155, 47, 42, 0.55);
  box-shadow: 0 0 0 2px rgba(155, 47, 42, 0.1);
}

.trade-badge strong {
  justify-content: center;
  border-color: rgba(111, 20, 24, 0.34);
  color: #fff7ea;
  background:
    linear-gradient(135deg, rgba(111, 20, 24, 0.92), rgba(185, 91, 41, 0.9)),
    #8b2a25;
  box-shadow: inset 0 0 0 1px rgba(255, 247, 234, 0.26);
}

.trade-badge.is-known strong {
  background:
    linear-gradient(135deg, rgba(39, 59, 88, 0.94), rgba(47, 111, 109, 0.86)),
    #273b58;
}

.trade-badge.is-inferred strong {
  background:
    linear-gradient(135deg, rgba(111, 20, 24, 0.94), rgba(194, 135, 50, 0.92)),
    #8b2a25;
}

.heatmap-wrap {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: transparent;
}

.trade-heatmap {
  display: block;
  width: 100%;
  height: 100%;
}

.trade-heatmap :deep(.heatmap-title) {
  fill: #352d27;
  font-size: 12px;
  font-weight: 800;
}

.trade-heatmap :deep(.axis path) {
  display: none;
}

.trade-heatmap :deep(.axis text) {
  fill: #3d3935;
  font-size: 20px;
  font-weight: 700;
}

.trade-heatmap :deep(.axis-x text) {
  font-size: 20px;
}

.trade-heatmap :deep(.legend-text) {
  fill: #6c6259;
  font-size: 10px;
  font-weight: 700;
}

.heatmap-tooltip {
  position: absolute;
  z-index: 3;
  display: grid;
  gap: 3px;
  max-width: 200px;
  padding: 7px 9px;
  border: 1px solid rgba(84, 55, 38, 0.16);
  border-radius: 6px;
  color: #3b3029;
  background: rgba(255, 252, 244, 0.96);
  box-shadow: 0 8px 20px rgba(61, 47, 38, 0.18);
  font-size: 11px;
  line-height: 1.45;
  opacity: 0;
  pointer-events: none;
  transform: translateY(4px);
  transition:
    opacity 0.12s ease,
    transform 0.12s ease;
}

.heatmap-tooltip b {
  color: #7b2723;
  font-weight: 800;
}

.heatmap-tooltip.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.chart-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #6a5b4f;
  font-size: 12px;
  pointer-events: none;
}

.chart-state--error {
  color: #9b2f2a;
}

@media (max-width: 980px) {
  .role-selector {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
