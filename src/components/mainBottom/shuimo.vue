<template>
  <div class="stage-river-panel">
    <div class="chart-toolbar">
      <label class="script-field">
        <span>剧本</span>
        <select v-model="selectedScriptKey" @change="handleScriptChange">
          <option v-for="script in scriptOptions" :key="script.key" :value="script.key">
            {{ script.name }}
          </option>
        </select>
      </label>
    </div>

    <div ref="chartBodyRef" class="chart-body">
      <svg ref="svgRef" class="river-svg" role="img" aria-label="阶段主题河流图"></svg>
      <div ref="tooltipRef" class="river-tooltip"></div>
      <div v-if="loading" class="chart-state">数据加载中...</div>
      <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
      <div v-else-if="!hasRiverData" class="chart-state">暂无河流图数据</div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'

const SCENE_URL = '/数据表合集/4/Table1_Scene_Sequence_Analysis (1).csv'
const STAGE_URL = '/数据表合集/4/Table2_Core_Stages_Analysis (1).csv'

const width = 560
const height = 246

const margin = {
  top: 42,
  right: 18,
  bottom: 44,
  left: 62,
}

const metricFields = [
  { key: 'performanceDensity', label: '表演形式密度', aggregate: 'avg' },
  { key: 'conflictStrength', label: '冲突强度', aggregate: 'avg' },
  { key: 'emotionStrength', label: '情绪强度', aggregate: 'avg' },
  { key: 'roleActivity', label: '角色活跃度', aggregate: 'avg' },
  { key: 'relationChanges', label: '关系变化次数', aggregate: 'sum' },
  { key: 'plotStrength', label: '综合剧情强度', aggregate: 'avg' },
]

const colorMap = {
  performanceDensity: '#8f3f2f',
  conflictStrength: '#c59a4b',
  emotionStrength: '#3f6f68',
  roleActivity: '#5d6470',
  relationChanges: '#9b6a4c',
  plotStrength: '#2f4f63',
}

const inkColorMap = {
  performanceDensity: ['#b85a43', '#8f3f2f'],
  conflictStrength: ['#d2a94f', '#c59a4b'],
  emotionStrength: ['#5e9b90', '#3f6f68'],
  roleActivity: ['#7b8492', '#5d6470'],
  relationChanges: ['#b57a55', '#9b6a4c'],
  plotStrength: ['#4f7488', '#2f4f63'],
}

const stageOrder = ['开端', '发展', '高潮', '结局']

const chartBodyRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)
const sceneRows = ref([])
const stageRows = ref([])
const selectedScriptKey = ref('')
const loading = ref(false)
const errorMessage = ref('')
let resizeObserver = null
let drawFrame = 0

const uid = `river-${Math.random().toString(36).slice(2, 10)}`

const scriptOptions = computed(() => {
  const scripts = new Map()

  for (const row of sceneRows.value) {
    if (row.scriptId && row.scriptName) scripts.set(row.scriptId, row.scriptName)
  }

  for (const row of stageRows.value) {
    if (row.scriptId && row.scriptName) scripts.set(row.scriptId, row.scriptName)
  }

  return Array.from(scripts, ([id, name]) => ({
    id,
    name,
    key: `${id}__${name}`,
  })).sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
})

const selectedScript = computed(() => {
  const [id = '', name = ''] = selectedScriptKey.value.split('__')
  return { id, name }
})

const currentSceneRows = computed(() =>
  sceneRows.value
    .filter((row) => row.scriptId === selectedScript.value.id)
    .sort((a, b) => a.sequence - b.sequence),
)

const currentStageRows = computed(() =>
  stageRows.value
    .filter((row) => row.scriptId === selectedScript.value.id)
    .sort((a, b) => getSceneOrder(a.startScene) - getSceneOrder(b.startScene)),
)

const stagePoints = computed(() => {
  const sceneOrderMap = new Map(
    currentSceneRows.value.map((row) => [normalizeSceneName(row.sceneName), row.sequence]),
  )
  const stageMap = new Map()

  currentStageRows.value.forEach((stage, index) => {
    const startSceneName = normalizeSceneName(stage.startScene)
    const endSceneName = normalizeSceneName(stage.endScene)

    const startOrder = sceneOrderMap.get(startSceneName) ?? getSceneOrder(stage.startScene) ?? index + 1
    const endOrder = sceneOrderMap.get(endSceneName) ?? getSceneOrder(stage.endScene) ?? startOrder

    let stageScenes = currentSceneRows.value.filter(
      (row) => row.sequence >= startOrder && row.sequence <= endOrder,
    )

    // 关键兜底：如果阶段表的起止场次名称和场景表对不上，
    // 就直接按照“开端/发展/高潮/结局”来取当前剧本自己的场景数据。
    // 这样切换剧本后，河流形状会真正跟着当前剧本的数据变化。
    if (!stageScenes.length) {
      stageScenes = currentSceneRows.value.filter(
        (row) => normalizeStageType(row.stageType) === normalizeStageType(stage.stageType),
      )
    }

    stageMap.set(normalizeStageType(stage.stageType), {
      name: normalizeStageType(stage.stageType),
      range: `${stage.startScene}-${stage.endScene}`,
      summary: stage.summary,
      rhythm: stage.rhythm,
      sceneCount: stageScenes.length,
      values: Object.fromEntries(
        metricFields.map((metric) => [
          metric.key,
          aggregateMetric(stageScenes, metric.key, metric.aggregate),
        ]),
      ),
    })
  })

  const sceneStageMap = new Map()

  for (const row of currentSceneRows.value) {
    if (!row.stageType) continue
    if (!sceneStageMap.has(row.stageType)) sceneStageMap.set(row.stageType, [])
    sceneStageMap.get(row.stageType).push(row)
  }

  for (const [stageType, rows] of sceneStageMap) {
    const normalizedStageType = normalizeStageType(stageType)
    if (stageMap.has(normalizedStageType)) continue

    stageMap.set(normalizedStageType, {
      name: stageType,
      range: `${rows[0].sceneName}-${rows.at(-1).sceneName}`,
      summary: rows.map((row) => row.summary).filter(Boolean).join('；'),
      rhythm: '',
      sceneCount: rows.length,
      values: Object.fromEntries(
        metricFields.map((metric) => [
          metric.key,
          aggregateMetric(rows, metric.key, metric.aggregate),
        ]),
      ),
    })
  }

  return stageOrder.map((stageName, index) => ({
    index,
    name: stageName,
    range: stageMap.get(stageName)?.range || '暂无场次',
    summary: stageMap.get(stageName)?.summary || '',
    rhythm: stageMap.get(stageName)?.rhythm || '',
    sceneCount: stageMap.get(stageName)?.sceneCount || 0,
    values:
      stageMap.get(stageName)?.values ||
      Object.fromEntries(metricFields.map((metric) => [metric.key, 0])),
  }))
})

const riverRows = computed(() =>
  stagePoints.value.map((stage) => ({
    index: stage.index,
    stage,
    ...Object.fromEntries(
      metricFields.map((metric) => [
        metric.key,
        Number(stage.values[metric.key].toFixed(2)),
      ]),
    ),
  })),
)

const hasRiverData = computed(() =>
  riverRows.value.some((row) => metricFields.some((metric) => row[metric.key] > 0)),
)

onMounted(async () => {
  await loadData()
  await nextTick()
  scheduleDraw()

  resizeObserver = new ResizeObserver(scheduleDraw)
  if (chartBodyRef.value) resizeObserver.observe(chartBodyRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (drawFrame) cancelAnimationFrame(drawFrame)
  d3.select(svgRef.value).selectAll('*').remove()
})

watch(scriptOptions, (nextOptions) => {
  if (!nextOptions.length) {
    selectedScriptKey.value = ''
    return
  }

  if (!nextOptions.some((script) => script.key === selectedScriptKey.value)) {
    selectedScriptKey.value = nextOptions[0].key
  }
})

watch(selectedScriptKey, async () => {
  await nextTick()
  scheduleDraw()
})

watch(riverRows, async () => {
  await nextTick()
  scheduleDraw()
}, { deep: true })

function handleScriptChange() {
  hideTooltip()
  scheduleDraw()
}

function scheduleDraw() {
  if (drawFrame) cancelAnimationFrame(drawFrame)

  drawFrame = requestAnimationFrame(() => {
    drawFrame = 0
    drawRiver()
  })
}

async function loadData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [sceneData, stageData] = await Promise.all([
      d3.csv(encodeURI(SCENE_URL), normalizeSceneRow),
      d3.csv(encodeURI(STAGE_URL), normalizeStageRow),
    ])

    sceneRows.value = sceneData.filter((row) => row.scriptId && row.scriptName)
    stageRows.value = stageData.filter((row) => row.scriptId && row.scriptName && row.stageType)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据读取失败'
  } finally {
    loading.value = false
  }
}

function drawRiver() {
  if (!svgRef.value || !chartBodyRef.value) return

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  const bodyRect = chartBodyRef.value.getBoundingClientRect()
  const chartWidth = Math.max(width, bodyRect.width || width)
  const chartHeight = Math.max(180, bodyRect.height || height)

  const innerWidth = Math.max(10, chartWidth - margin.left - margin.right)
  const innerHeight = Math.max(10, chartHeight - margin.top - margin.bottom)

  svg
    .attr('viewBox', `0 0 ${chartWidth} ${chartHeight}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  if (!hasRiverData.value) return

  const rows = riverRows.value
  const keys = metricFields.map((metric) => metric.key)

  const layers = d3.stack()
  .keys(keys)
  .offset(d3.stackOffsetSilhouette)
  .order(d3.stackOrderInsideOut)(rows)

const yExtent = [
  d3.min(layers, (layer) => d3.min(layer, (point) => point[0])) || 0,
  d3.max(layers, (layer) => d3.max(layer, (point) => point[1])) || 1,
]

  /**
   * 关键修改 1：
   * 这里不要用 scalePoint + padding。
   * scalePoint 会让第一个点离 y 轴有一段距离，所以视觉上面积图不会贴着 y 轴。
   * 改用 scaleLinear，明确让 index=0 对应 x=0，最后一个阶段对应 x=innerWidth。
   */
  const x = d3.scaleLinear()
  .domain([0, rows.length - 1])  // 从第一个阶段到最后一个阶段
  .range([0, innerWidth])


  /**
   * 关键修改 2：
   * y(0) 必须严格等于 innerHeight，也就是 x 轴的位置。
   * y(yMax) 严格等于 0，也就是绘图区顶部。
   */
  const y = d3.scaleLinear()
  .domain(yExtent)
  .range([innerHeight, 0])
  .nice()

  const clampX = (value) => Math.max(0, Math.min(innerWidth, value))
  const clampYValue = (value) => Math.max(yExtent[0], Math.min(yExtent[1], value))

  /**
   * 关键修改 3：
   * area 的 x/y 坐标全部 clamp，保证生成出来的 path 不主动越界。
   * curveLinear 最稳，绝对不会因为平滑曲线产生外溢。
   * 如果你想稍微软一点，可以把 curveLinear 改成 curveMonotoneX，
   * 但最稳妥、绝不超出范围的是 curveLinear。
   */
  const area = d3.area()
  .x((point) => clampX(x(point.data.index)))
  .y0((point) => y(clampYValue(point[0])))
  .y1((point) => y(clampYValue(point[1])))
  .curve(d3.curveMonotoneX)

  const defs = svg.append('defs')

  const clipId = `${uid}-clip`
  const paperFilterId = `${uid}-paper-texture`
const inkBlurFilterId = `${uid}-ink-blur`
const inkEdgeFilterId = `${uid}-ink-edge`

const inkBlurFilter = defs.append('filter')
  .attr('id', inkBlurFilterId)
  .attr('x', '-15%')
  .attr('y', '-15%')
  .attr('width', '130%')
  .attr('height', '130%')

inkBlurFilter.append('feGaussianBlur')
  .attr('stdDeviation', 1.4)
  .attr('result', 'blur')

inkBlurFilter.append('feColorMatrix')
  .attr('type', 'matrix')
  .attr('values', `
    1 0 0 0 0
    0 1 0 0 0
    0 0 1 0 0
    0 0 0 0.72 0
  `)

const inkEdgeFilter = defs.append('filter')
  .attr('id', inkEdgeFilterId)
  .attr('x', '-10%')
  .attr('y', '-10%')
  .attr('width', '120%')
  .attr('height', '120%')

inkEdgeFilter.append('feTurbulence')
  .attr('type', 'fractalNoise')
  .attr('baseFrequency', '0.035')
  .attr('numOctaves', 2)
  .attr('seed', 12)
  .attr('result', 'noise')

inkEdgeFilter.append('feDisplacementMap')
  .attr('in', 'SourceGraphic')
  .attr('in2', 'noise')
  .attr('scale', 3.2)
  .attr('xChannelSelector', 'R')
  .attr('yChannelSelector', 'G')
  /**
   * 关键修改 4：
   * 裁剪框的坐标和 plotGroup 内部坐标完全一致。
   * 也就是说，河流图层只能显示在：
   * x: 0 ~ innerWidth
   * y: 0 ~ innerHeight
   * 这个矩形中。
   */
  defs.append('clipPath')
    .attr('id', clipId)
    .attr('clipPathUnits', 'userSpaceOnUse')
    .append('rect')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', innerWidth)
    .attr('height', innerHeight)

  const paperFilter = defs.append('filter')
    .attr('id', paperFilterId)
    .attr('filterUnits', 'objectBoundingBox')
    .attr('x', '0')
    .attr('y', '0')
    .attr('width', '1')
    .attr('height', '1')

  paperFilter.append('feTurbulence')
    .attr('type', 'fractalNoise')
    .attr('baseFrequency', '0.018')
    .attr('numOctaves', '3')
    .attr('seed', '8')
    .attr('result', 'noise')

  paperFilter.append('feColorMatrix')
    .attr('type', 'matrix')
    .attr('values', `
      0.18 0    0    0 0.82
      0    0.14 0    0 0.78
      0    0    0.10 0 0.68
      0    0    0    0.10 0
    `)

  metricFields.forEach((metric) => {
    const [lightColor, darkColor] = inkColorMap[metric.key]
    const gradientId = `${uid}-ink-gradient-${metric.key}`

    const gradient = defs.append('linearGradient')
      .attr('id', gradientId)
      .attr('gradientUnits', 'userSpaceOnUse')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', 0)
      .attr('y2', 0)

    gradient.append('stop')
  .attr('offset', '0%')
  .attr('stop-color', lightColor)
  .attr('stop-opacity', 0.9)

gradient.append('stop')
  .attr('offset', '50%')
  .attr('stop-color', darkColor)
  .attr('stop-opacity', 1)

gradient.append('stop')
  .attr('offset', '100%')
  .attr('stop-color', lightColor)
  .attr('stop-opacity', 0.9)
  })

  

  const plotGroup = svg.append('g')
    .attr('class', 'plot-group')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  
  const gridGroup = plotGroup.append('g')
    .attr('class', 'grid-group')

  const riverGroup = plotGroup.append('g')
    .attr('class', 'river-group')
    .attr('clip-path', `url(#${clipId})`)

  const axisGroup = plotGroup.append('g')
    .attr('class', 'axis-group')

  gridGroup.append('g')
    .attr('class', 'grid-lines')
    .call(d3.axisLeft(y).ticks(4).tickSize(-innerWidth).tickFormat(''))
    .call((group) => group.select('.domain').remove())

  const layerGroups = riverGroup.selectAll('.river-layer-group')
  .data(layers)
  .join('g')
  .attr('class', 'river-layer-group')

layerGroups.append('path')
  .attr('class', 'river-layer river-layer--wash')
  .attr('d', area)
  .attr('fill', (layer) => colorMap[layer.key])
  .attr('fill-opacity', 0.16)
  .attr('stroke', 'none')
  .attr('filter', `url(#${inkBlurFilterId})`)

layerGroups.append('path')
  .attr('class', 'river-layer river-layer--ink')
  .attr('d', area)
  .attr('fill', (layer) => `url(#${uid}-ink-gradient-${layer.key})`)
  .attr('fill-opacity', 0.72)
  .attr('stroke', (layer) => colorMap[layer.key])
  .attr('stroke-width', 0.9)
  .attr('stroke-opacity', 0.38)
  .attr('filter', `url(#${inkEdgeFilterId})`)

layerGroups.append('path')
  .attr('class', 'river-layer river-layer--edge')
  .attr('d', area)
  .attr('fill', 'none')
  .attr('stroke', (layer) => colorMap[layer.key])
  .attr('stroke-width', 1.8)
  .attr('stroke-opacity', 0.18)
  .attr('stroke-linejoin', 'round')
  .attr('stroke-linecap', 'round')
  .attr('filter', `url(#${inkBlurFilterId})`)

layerGroups
  .on('mouseenter', function () {
    riverGroup.selectAll('.river-layer-group')
      .attr('opacity', 0.28)

    d3.select(this)
      .attr('opacity', 1)

    d3.select(this).select('.river-layer--ink')
      .attr('fill-opacity', 0.88)
      .attr('stroke-opacity', 0.62)
      .attr('stroke-width', 1.2)
  })
  .on('mouseleave', function () {
    riverGroup.selectAll('.river-layer-group')
      .attr('opacity', 1)

    d3.select(this).select('.river-layer--ink')
      .attr('fill-opacity', 0.72)
      .attr('stroke-opacity', 0.38)
      .attr('stroke-width', 0.9)

    hideTooltip()
    focusLine.attr('opacity', 0)
  })
  .on('mousemove', function (event, layer) {
    const pointerX = d3.pointer(event, plotGroup.node())[0]
    const currentRow = nearestRow(rows, pointerX, x)

    focusLine
      .attr('x1', x(currentRow.index))
      .attr('x2', x(currentRow.index))
      .attr('opacity', 1)

    showTooltip(event, currentRow, layer.key)
  })

  const focusLine = axisGroup.append('line')
    .attr('class', 'focus-line')
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('opacity', 0)

  const yAxis = axisGroup.append('g')
    .attr('class', 'y-axis')
    .call(d3.axisLeft(y).ticks(4).tickFormat((value) => formatValue(value)))

  yAxis.selectAll('.tick text')
    .attr('dx', -4)

  axisGroup.append('text')
    .attr('class', 'axis-title axis-title--y')
    .attr('x', -innerHeight / 2)
    .attr('y', -46)
    .attr('transform', 'rotate(-90)')
    .attr('text-anchor', 'middle')
    .text('指标强度')

  const xAxis = axisGroup.append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(
      d3.axisBottom(x)
        .tickValues(rows.map((row) => row.index))
        .tickFormat((value) => rows.find((row) => row.index === value)?.stage.name || value),
    )

  xAxis.selectAll('.tick text')
    .attr('dy', 13)

  axisGroup.append('text')
    .attr('class', 'axis-title axis-title--x')
    .attr('x', innerWidth / 2)
    .attr('y', innerHeight + 38)
    .attr('text-anchor', 'middle')
    .text('剧情阶段')

  axisGroup.raise()

  const legend = svg.append('g')
    .attr('class', 'legend')
    .attr('transform', `translate(${margin.left},16)`)

  const legendItems = legend.selectAll('.legend-item')
    .data(metricFields)
    .join('g')
    .attr('class', 'legend-item')
    .attr('transform', (metric, index) => {
      const col = index % 3
      const row = Math.floor(index / 3)
      return `translate(${col * 116},${row * 16})`
    })

  legendItems.append('circle')
  .attr('cx', 4.5)
  .attr('cy', 4.5)
  .attr('r', 4.5)
  .attr('fill', (metric) => `url(#${uid}-ink-gradient-${metric.key})`)
  .attr('stroke', (metric) => colorMap[metric.key])
  .attr('stroke-width', 0.6)
  .attr('opacity', 1)

  legendItems.append('text')
    .attr('x', 13)
    .attr('y', 8)
    .text((metric) => metric.label)
}

function showTooltip(event, row, activeKey) {
  if (!tooltipRef.value || !chartBodyRef.value) return

  const stage = row.stage
  const activeMetric = metricFields.find((metric) => metric.key === activeKey)

  const values = metricFields
    .slice()
    .sort((a, b) => row[b.key] - row[a.key])
    .map((metric) => {
      const activeClass = metric.key === activeKey ? ' river-tooltip__active' : ''
      return `<div class="river-tooltip__row${activeClass}"><span style="background:${colorMap[metric.key]}"></span>${metric.label}<strong>${formatValue(row[metric.key])}</strong></div>`
    })
    .join('')

  tooltipRef.value.innerHTML = `
    <div class="river-tooltip__title">${stage.name}（${stage.range}）</div>
    <div class="river-tooltip__meta">包含场次：${stage.sceneCount}</div>
    ${stage.rhythm ? `<div class="river-tooltip__meta">节奏变化：${stage.rhythm}</div>` : ''}
    ${stage.summary ? `<div class="river-tooltip__meta">关键事件：${stage.summary}</div>` : ''}
    <div class="river-tooltip__metric">当前指标：${activeMetric?.label || ''}</div>
    ${values}
  `

  const bodyRect = chartBodyRef.value.getBoundingClientRect()
  const tooltipWidth = 218
  const tooltipHeight = 140

  const x = Math.min(
    Math.max(event.clientX - bodyRect.left + 14, 6),
    Math.max(6, bodyRect.width - tooltipWidth - 8),
  )

  const y = Math.min(
    Math.max(event.clientY - bodyRect.top - 20, 6),
    Math.max(6, bodyRect.height - tooltipHeight - 8),
  )

  tooltipRef.value.style.transform = `translate(${x}px, ${y}px)`
  tooltipRef.value.style.opacity = '1'
}

function hideTooltip() {
  if (tooltipRef.value) tooltipRef.value.style.opacity = '0'
}

function nearestRow(rows, pointerX, xScale) {
  return rows.reduce((nearest, row) => {
    const currentDistance = Math.abs(xScale(row.index) - pointerX)
    const nearestDistance = Math.abs(xScale(nearest.index) - pointerX)
    return currentDistance < nearestDistance ? row : nearest
  }, rows[0])
}

function normalizeSceneRow(row) {
  const sceneWithStage = text(row['事件/场次ID【阶段】'])

  return {
    scriptId: text(row['剧本id']),
    scriptName: text(row['剧本名称']),
    sceneName: sceneWithStage.replace(/【.*?】/g, ''),
    stageType: sceneWithStage.match(/【(.*?)】/)?.[1] || '',
    sequence: toNumber(row['顺序编号']),
    performanceDensity: toNumber(row['表演形式密度']),
    conflictStrength: toNumber(row['冲突强度']),
    emotionStrength: toNumber(row['情绪强度']),
    roleActivity: toNumber(row['角色活跃度']),
    relationChanges: toNumber(row['关系变化次数']),
    plotStrength: toNumber(row['综合剧情强度']),
    summary: text(row['关键事件摘要']),
  }
}

function normalizeStageRow(row) {
  return {
    scriptId: text(row['剧本id']),
    scriptName: text(row['剧本名']),
    stageType: text(row['阶段类型']),
    startScene: text(row['起始事件/场次']),
    endScene: text(row['结束事件/场次']),
    summary: text(row['关键事件摘要']),
    rhythm: text(row['节奏变化']),
  }
}

function aggregateMetric(rows, key, mode) {
  const values = rows.map((row) => row[key]).filter((value) => Number.isFinite(value))
  if (!values.length) return 0

  const total = values.reduce((sum, value) => sum + value, 0)
  return mode === 'sum' ? total : total / values.length
}

function getSceneOrder(sceneName) {
  const match = text(sceneName).match(/[第]?(.*?)[场幕]/)
  if (!match) return 0

  return chineseNumberToInt(match[1])
}

function chineseNumberToInt(value) {
  const textValue = text(value)
  const directNumber = Number(textValue)
  if (Number.isFinite(directNumber)) return directNumber

  const digits = {
    零: 0,
    一: 1,
    二: 2,
    两: 2,
    三: 3,
    四: 4,
    五: 5,
    六: 6,
    七: 7,
    八: 8,
    九: 9,
  }

  if (textValue === '十') return 10

  if (textValue.includes('十')) {
    const [tensText, onesText] = textValue.split('十')
    const tens = tensText ? digits[tensText] || 0 : 1
    const ones = onesText ? digits[onesText] || 0 : 0
    return tens * 10 + ones
  }

  return digits[textValue] || 0
}

function normalizeSceneName(value) {
  return text(value)
    .replace(/【.*?】/g, '')
    .replace(/\s+/g, '')
    .replace(/[：:，,。、《》<>]/g, '')
}

function normalizeStageType(value) {
  return text(value).replace(/\s+/g, '')
}

function text(value) {
  return String(value ?? '').trim()
}

function toNumber(value) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

function formatValue(value) {
  return Number(value).toLocaleString('zh-CN', {
    maximumFractionDigits: 2,
  })
}
</script>

<style scoped>
.stage-river-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 6px;
  border: 1px solid rgba(93, 72, 54, 0.16);
  border-radius: 14px;
  background:
    radial-gradient(circle at 16% 18%, rgba(180, 139, 89, 0.14), transparent 28%),
    radial-gradient(circle at 84% 12%, rgba(63, 111, 104, 0.12), transparent 30%),
    linear-gradient(135deg, rgba(250, 244, 228, 0.96), rgba(238, 228, 203, 0.9));
  box-shadow:
    inset 0 0 30px rgba(120, 96, 67, 0.08),
    0 10px 26px rgba(55, 44, 33, 0.08);
  overflow: hidden;
}

.stage-river-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.26;
  background-image:
    linear-gradient(90deg, rgba(86, 69, 48, 0.04) 1px, transparent 1px),
    linear-gradient(0deg, rgba(86, 69, 48, 0.035) 1px, transparent 1px);
  background-size: 18px 18px, 22px 22px;
  mix-blend-mode: multiply;
}

.chart-toolbar {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  min-height: 30px;
  padding: 0 8px 4px;
}

.script-field {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #5d4c3d;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.script-field span {
  font-weight: 800;
}

.script-field select {
  width: 126px;
  height: 25px;
  border: 1px solid rgba(93, 72, 54, 0.24);
  border-radius: 999px;
  padding: 0 24px 0 10px;
  color: #4b3c31;
  font-size: 12px;
  background:
    linear-gradient(180deg, rgba(255, 252, 242, 0.88), rgba(239, 227, 202, 0.84));
  outline: none;
  box-shadow: inset 0 0 8px rgba(122, 95, 61, 0.08);
}

.script-field select:focus {
  border-color: rgba(143, 63, 47, 0.5);
  box-shadow:
    0 0 0 2px rgba(143, 63, 47, 0.1),
    inset 0 0 8px rgba(122, 95, 61, 0.08);
}

.chart-body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.river-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.river-svg :deep(.ink-mountain) {
  pointer-events: none;
}

.river-svg :deep(.ink-mountain--back) {
  fill: rgba(82, 102, 91, 0.09);
  filter: blur(0.3px);
}

.river-svg :deep(.ink-mountain--front) {
  fill: rgba(99, 77, 56, 0.08);
  filter: blur(0.2px);
}

.river-svg :deep(.grid-lines line) {
  stroke: rgba(77, 63, 48, 0.08);
  stroke-dasharray: 2 7;
}

.river-svg :deep(.grid-lines path) {
  display: none;
}

.river-svg :deep(.x-axis path),
.river-svg :deep(.y-axis path) {
  stroke: rgba(74, 58, 43, 0.38);
  stroke-width: 1;
}

.river-svg :deep(.x-axis line),
.river-svg :deep(.y-axis line) {
  stroke: rgba(74, 58, 43, 0.28);
}

.river-svg :deep(.x-axis text),
.river-svg :deep(.y-axis text),
.river-svg :deep(.axis-title),
.river-svg :deep(.legend text) {
  fill: rgba(46, 36, 29, 0.92);
  font-family:
    "STKaiti",
    "KaiTi",
    "FangSong",
    "Microsoft YaHei",
    sans-serif;
}

.river-svg :deep(.x-axis text) {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.river-svg :deep(.y-axis text) {
  font-size: 10px;
  font-weight: 700;
  opacity: 0.88;
}

.river-svg :deep(.axis-title) {
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.river-svg :deep(.legend text) {
  font-size: 10px;
  opacity: 0.88;
}

.river-svg :deep(.legend circle) {
  filter: drop-shadow(0 1px 2px rgba(72, 55, 40, 0.16));
}

.river-svg :deep(.river-layer) {
  cursor: pointer;
  transition:
    fill-opacity 0.18s ease,
    stroke-width 0.18s ease,
    filter 0.18s ease;
}

.river-svg :deep(.focus-line) {
  stroke: rgba(55, 43, 34, 0.34);
  stroke-width: 1;
  stroke-dasharray: 2 5;
  pointer-events: none;
}

.river-tooltip {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  width: 218px;
  padding: 10px 11px;
  border: 1px solid rgba(108, 77, 48, 0.24);
  border-radius: 10px;
  color: #49382f;
  font-size: 11px;
  line-height: 1.55;
  background:
    linear-gradient(135deg, rgba(255, 252, 242, 0.96), rgba(239, 228, 203, 0.94));
  box-shadow:
    0 10px 24px rgba(69, 52, 37, 0.16),
    inset 0 0 16px rgba(142, 111, 72, 0.08);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
  backdrop-filter: blur(3px);
}

.river-tooltip :deep(.river-tooltip__title) {
  margin-bottom: 4px;
  color: #2f4f63;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.06em;
}

.river-tooltip :deep(.river-tooltip__meta) {
  margin-bottom: 3px;
  color: #75614f;
}

.river-tooltip :deep(.river-tooltip__metric) {
  margin: 6px 0 4px;
  color: #8f3f2f;
  font-weight: 800;
}

.river-tooltip :deep(.river-tooltip__row) {
  display: grid;
  grid-template-columns: 9px 1fr auto;
  gap: 6px;
  align-items: center;
  margin-top: 2px;
}

.river-tooltip :deep(.river-tooltip__row span) {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.river-tooltip :deep(.river-tooltip__row strong) {
  font-weight: 900;
}

.river-tooltip :deep(.river-tooltip__active) {
  color: #8f3f2f;
  font-weight: 800;
}

.chart-state {
  position: absolute;
  inset: 34px 12px 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #75614f;
  font-size: 13px;
  background: rgba(250, 244, 228, 0.72);
}

.chart-state--error {
  color: #8f3f2f;
}
</style>
