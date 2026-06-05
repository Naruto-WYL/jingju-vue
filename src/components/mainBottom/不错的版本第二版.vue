<template>
  <div class="stage-river-panel">
    <div class="chart-toolbar" :class="{ 'chart-toolbar--teleported': props.selectTarget }">
      <Teleport v-if="props.selectTarget" :to="props.selectTarget" defer>
        <select
          v-model="selectedScriptKey"
          class="script-select"
          aria-label="选择剧本"
          :disabled="loading || !scriptOptions.length"
        >
          <option v-for="script in scriptOptions" :key="script.key" :value="script.key">
            {{ script.name }}
          </option>
        </select>
      </Teleport>
      <label v-else class="script-field">
        <span>剧本</span>
        <select
          v-model="selectedScriptKey"
          class="script-select"
          aria-label="选择剧本"
          :disabled="loading || !scriptOptions.length"
        >
          <option v-for="script in scriptOptions" :key="script.key" :value="script.key">
            {{ script.name }}
          </option>
        </select>
      </label>
    </div>

    <div class="chart-content">
      <div ref="chartBodyRef" class="chart-body">
        <svg ref="svgRef" class="river-svg" role="img" aria-label="剧情节奏河流图"></svg>
        <div ref="tooltipRef" class="river-tooltip"></div>
        <div v-if="loading" class="chart-state">数据加载中...</div>
        <div v-else-if="errorMessage" class="chart-state chart-state--error">{{ errorMessage }}</div>
        <div v-else-if="!hasRiverData" class="chart-state">暂无河流图数据</div>
      </div>

      <aside class="stage-side-panel" aria-label="叙事阶段场次范围">
        <div
          v-for="band in stageBands"
          :key="`${band.name}-${band.startIndex}-${band.endIndex}`"
          class="stage-card"
          :style="stageCardStyle(band)"
        >
          <span class="stage-card__name">{{ band.name }}</span>
          <strong class="stage-card__range">{{ formatStageRangeText(band) }}</strong>
        </div>
      </aside>
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
  right: 10,
  bottom: 50,
  left: 30,
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
  performanceDensity: '#8f2f2a',
  conflictStrength: '#b88a36',
  emotionStrength: '#2f625d',
  roleActivity: '#3d4655',
  relationChanges: '#9a5260',
  plotStrength: '#5c5360',
}

const inkColorMap = {
  performanceDensity: ['#f3ded7', '#8f2f2a'],
  conflictStrength: ['#f0ddb0', '#a57427'],
  emotionStrength: ['#d4e5e1', '#2f625d'],
  roleActivity: ['#d7dce3', '#3d4655'],
  relationChanges: ['#ecd2d6', '#9a5260'],
  plotStrength: ['#ded8e0', '#5c5360'],
}

const stageColorMap = {
  开端: '#5f7b68',
  发展: '#bd8841',
  转折: '#8d657d',
  高潮: '#b85a63',
  结局: '#3f6581',
}

const props = defineProps({
  selectTarget: {
    type: String,
    default: '',
  },
})

const chartBodyRef = ref(null)
const svgRef = ref(null)
const tooltipRef = ref(null)
const sceneRows = ref([])
const stageRows = ref([])
const selectedScriptKey = ref('')
const loading = ref(false)
const errorMessage = ref('')
let resizeObserver = null

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

const stageBands = computed(() => {
  const scenes = currentSceneRows.value
  if (!scenes.length) return []

  const sceneOrderMap = new Map(scenes.map((row) => [row.sceneName, row.sequence]))
  const indexBySequence = new Map(scenes.map((row, index) => [row.sequence, index]))
  const bands = currentStageRows.value
    .map((stage, index) => {
      const startOrder = sceneOrderMap.get(stage.startScene) ?? getSceneOrder(stage.startScene) ?? index + 1
      const endOrder = sceneOrderMap.get(stage.endScene) ?? getSceneOrder(stage.endScene) ?? startOrder
      const startIndex = resolveSceneIndex(scenes, indexBySequence, startOrder, 'start')
      const endIndex = resolveSceneIndex(scenes, indexBySequence, endOrder, 'end')

      if (startIndex < 0 || endIndex < startIndex) return null

      return {
        name: stage.stageType,
        startIndex,
        endIndex,
        startNumber: scenes[startIndex]?.sequence || startOrder,
        endNumber: scenes[endIndex]?.sequence || endOrder,
        range: `${stage.startScene}-${stage.endScene}`,
        summary: stage.summary,
        rhythm: stage.rhythm,
        sceneCount: endIndex - startIndex + 1,
      }
    })
    .filter(Boolean)

  if (bands.length) return bands

  const fallbackBands = []
  let startIndex = 0
  let stageName = scenes[0].stageType || '未分段'

  for (let index = 1; index <= scenes.length; index += 1) {
    const nextStageName = scenes[index]?.stageType || '未分段'
    if (index < scenes.length && nextStageName === stageName) continue

    const rows = scenes.slice(startIndex, index)
    fallbackBands.push({
      name: stageName,
      startIndex,
      endIndex: index - 1,
      startNumber: rows[0]?.sequence || startIndex + 1,
      endNumber: rows.at(-1)?.sequence || index,
      range: `${rows[0]?.sceneName || ''}-${rows.at(-1)?.sceneName || ''}`,
      summary: rows.map((row) => row.summary).filter(Boolean).join('；'),
      rhythm: '',
      sceneCount: rows.length,
    })

    startIndex = index
    stageName = nextStageName
  }

  return fallbackBands
})

const stageBySceneIndex = computed(() => {
  const map = new Map()
  for (const band of stageBands.value) {
    for (let index = band.startIndex; index <= band.endIndex; index += 1) {
      map.set(index, band)
    }
  }
  return map
})

const riverRows = computed(() =>
  currentSceneRows.value.map((scene, index) => {
    const stage = stageBySceneIndex.value.get(index) || {
      name: scene.stageType || '未分段',
      range: scene.sceneName,
      summary: scene.summary,
      rhythm: '',
      sceneCount: 1,
    }

    return {
      index,
      scene,
      stage,
      sceneNumber: scene.sequence || index + 1,
      sceneLabel: numberToChinese(scene.sequence || index + 1),
      ...Object.fromEntries(metricFields.map((metric) => [metric.key, Number(scene[metric.key].toFixed(2))])),
    }
  }),
)

const hasRiverData = computed(() =>
  riverRows.value.some((row) => metricFields.some((metric) => row[metric.key] > 0)),
)

onMounted(async () => {
  await loadData()
  await nextTick()
  drawRiver()

  resizeObserver = new ResizeObserver(drawRiver)
  if (chartBodyRef.value) resizeObserver.observe(chartBodyRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
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

watch([riverRows, selectedScriptKey], async () => {
  await nextTick()
  drawRiver()
})

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
  const chartHeight = Math.max(210, bodyRect.height || height)
  const innerWidth = chartWidth - margin.left - margin.right
  const innerHeight = chartHeight - margin.top - margin.bottom

  svg.attr('viewBox', `0 0 ${chartWidth} ${chartHeight}`)

  if (!hasRiverData.value) return

  const rows = riverRows.value
  const keys = metricFields.map((metric) => metric.key)
  const waveRows = buildRiverWaveRows(rows, keys)
  const layers = d3.stack().keys(keys).offset(d3.stackOffsetNone)(waveRows)
  const yMax = d3.max(waveRows, (row) => d3.sum(keys, (key) => row[key])) || 1

  const xMax = Math.max(1, rows.length - 1)
  const x = d3.scaleLinear()
    .domain([0, xMax])
    .range([0, innerWidth])

  const y = d3.scaleLinear()
    .domain([0, yMax])
    .nice(4)
    .range([innerHeight, 0])

  const area = d3.area()
    .x(d => x(d.data.x))
    .y0(d => y(d[0]))
    .y1(d => y(d[1]))
    .curve(d3.curveBasis)

  const currentLine = d3.line()
    .x(d => x(d.data.x))
    .y(d => y(d[1]))
    .curve(d3.curveBasis)

  const defs = svg.append('defs')
  const paperFilterId = 'stage-river-paper-texture'
  const bleedFilterId = 'stage-river-ink-bleed'

  const paperFilter = defs.append('filter')
    .attr('id', paperFilterId)
    .attr('x', '-8%')
    .attr('y', '-8%')
    .attr('width', '116%')
    .attr('height', '116%')

  paperFilter.append('feTurbulence')
    .attr('type', 'fractalNoise')
    .attr('baseFrequency', '0.018')
    .attr('numOctaves', 3)
    .attr('seed', 12)
    .attr('result', 'noise')

  paperFilter.append('feDisplacementMap')
    .attr('in', 'SourceGraphic')
    .attr('in2', 'noise')
    .attr('scale', 0.95)
    .attr('xChannelSelector', 'R')
    .attr('yChannelSelector', 'G')

  const bleedFilter = defs.append('filter')
    .attr('id', bleedFilterId)
    .attr('x', '-10%')
    .attr('y', '-10%')
    .attr('width', '120%')
    .attr('height', '120%')

  bleedFilter.append('feGaussianBlur')
    .attr('stdDeviation', 1.85)
    .attr('result', 'softInk')

  metricFields.forEach((metric, index) => {
    const [lightColor, darkColor] = inkColorMap[metric.key]
    const gradient = defs.append('linearGradient')
      .attr('id', `stage-river-ink-${metric.key}`)
      .attr('gradientUnits', 'userSpaceOnUse')
      .attr('x1', 0)
      .attr('x2', innerWidth)
      .attr('y1', innerHeight * 0.12)
      .attr('y2', innerHeight)

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', lightColor)
      .attr('stop-opacity', 0.38)

    gradient.append('stop')
      .attr('offset', `${38 + index * 5}%`)
      .attr('stop-color', darkColor)
      .attr('stop-opacity', 0.82)

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', lightColor)
      .attr('stop-opacity', 0.44)
  })

  const root = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  root.append('g')
    .attr('class', 'grid-lines')
    .call(d3.axisLeft(y).ticks(4).tickSize(-innerWidth).tickFormat(''))
    .call((group) => group.select('.domain').remove())

  const yAxis = root.append('g')
    .attr('class', 'y-axis')
    .call(d3.axisLeft(y).ticks(4).tickFormat((value) => formatValue(value)))

  yAxis.selectAll('.tick text')
    .attr('dx', -4)

  root.append('text')
    .attr('class', 'axis-title')
    .attr('x', -innerHeight / 2)
    .attr('y', -42)
    .attr('transform', 'rotate(-90)')
    .attr('text-anchor', 'middle')
    .text('指标强度')

  const xAxis = root.append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(
      d3.axisBottom(x)
        .tickValues(rows.map((row) => row.index))
        .tickFormat((value) => rows.find((row) => row.index === value)?.sceneLabel || value),
    )

  xAxis.selectAll('.tick text')
    .attr('dx', -5)
    .attr('dy', 0)
    .attr('writing-mode', 'vertical-rl')
    .attr('text-anchor', 'start')

  const focusLine = root.append('line')
    .attr('class', 'focus-line')
    .attr('y1', 0)
    .attr('y2', innerHeight)
    .attr('opacity', 0)

  root.selectAll('.river-layer')
    .data(layers)
    .join('path')
    .attr('class', 'river-bleed')
    .attr('d', area)
    .attr('fill', (layer) => colorMap[layer.key])
    .attr('fill-opacity', 0.14)
    .attr('filter', `url(#${bleedFilterId})`)
    .attr('pointer-events', 'none')

  root.selectAll('.river-layer')
    .data(layers)
    .join('path')
    .attr('class', 'river-layer')
    .attr('d', area)
    .attr('fill', (layer) => `url(#stage-river-ink-${layer.key})`)
    .attr('stroke', 'rgba(62, 66, 68, 0.18)')
    .attr('stroke-width', 0.8)
    .attr('fill-opacity', 0.88)
    .attr('filter', `url(#${paperFilterId})`)
    .on('mouseenter', function () {
      d3.select(this).attr('fill-opacity', 1).attr('stroke-width', 1.2)
    })
    .on('mouseleave', function () {
      d3.select(this).attr('fill-opacity', 0.88).attr('stroke-width', 0.8)
      hideTooltip()
      focusLine.attr('opacity', 0)
    })
    .on('mousemove', function (event, layer) {
      const pointerX = d3.pointer(event, root.node())[0]
      const currentRow = nearestRow(rows, pointerX, x)
      focusLine.attr('x1', x(currentRow.index)).attr('x2', x(currentRow.index)).attr('opacity', 1)
      showTooltip(event, currentRow, layer.key)
    })

  root.selectAll('.river-current')
    .data(layers.slice(1, -1))
    .join('path')
    .attr('class', 'river-current')
    .attr('d', currentLine)
    .attr('fill', 'none')
    .attr('stroke', 'rgba(255, 255, 255, 0.42)')
    .attr('stroke-width', 0.72)
    .attr('stroke-linecap', 'round')
    .attr('stroke-dasharray', '1 7')
    .attr('pointer-events', 'none')

  const legend = svg.append('g')
    .attr('class', 'legend')
    .attr('transform', `translate(${margin.left},6)`)

  const legendItems = legend.selectAll('.legend-item')
    .data(metricFields)
    .join('g')
    .attr('class', 'legend-item')
    .attr('transform', (metric, index) => {
      const col = index % 3
      const row = Math.floor(index / 3)
      return `translate(${col * 122},${row * 18})`
    })

  legendItems.append('rect')
    .attr('width', 11)
    .attr('height', 11)
    .attr('rx', 2)
    .attr('fill', (metric) => colorMap[metric.key])

  legendItems.append('text')
    .attr('x', 16)
    .attr('y', 10)
    .text((metric) => metric.label)
}

function showTooltip(event, row, activeKey) {
  if (!tooltipRef.value || !chartBodyRef.value) return

  const stage = row.stage
  const scene = row.scene
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
    <div class="river-tooltip__title">${row.sceneLabel}（${stage.name}）</div>
    <div class="river-tooltip__meta">场次：${scene.sceneName}</div>
    <div class="river-tooltip__meta">阶段范围：${stage.range}</div>
    ${stage.rhythm ? `<div class="river-tooltip__meta">节奏变化：${stage.rhythm}</div>` : ''}
    ${scene.summary ? `<div class="river-tooltip__meta">关键事件：${scene.summary}</div>` : ''}
    <div class="river-tooltip__metric">当前指标：${activeMetric?.label || ''}</div>
    ${values}
  `

  const bodyRect = chartBodyRef.value.getBoundingClientRect()
  const x = Math.min(event.clientX - bodyRect.left + 14, bodyRect.width - 210)
  const y = Math.max(event.clientY - bodyRect.top - 20, 6)
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

function stageCardStyle(band) {
  const color = stageColorMap[band.name] || '#7a6658'
  return {
    '--stage-color': color,
  }
}

function formatStageRangeText(band) {
  const start = Number(band.startNumber || band.startIndex + 1)
  const end = Number(band.endNumber || band.endIndex + 1)

  if (!Number.isFinite(start) || !Number.isFinite(end)) return band.range || ''
  return start === end ? `第${numberToChinese(start)}场` : `第${numberToChinese(start)}-${numberToChinese(end)}场`
}

function buildRiverWaveRows(rows, keys) {
  const samplesPerStage = 34
  const waveRows = []

  if (rows.length === 1) {
    return [0, 1].map((x) => ({
      x,
      index: 0,
      stage: rows[0].stage,
      ...Object.fromEntries(keys.map((key) => [key, rows[0][key]])),
    }))
  }

  for (let i = 0; i < rows.length - 1; i += 1) {
    const current = rows[i]
    const next = rows[i + 1]

    for (let step = 0; step <= samplesPerStage; step += 1) {
      if (i > 0 && step === 0) continue

      const t = step / samplesPerStage
      const eased = smoothStep(t)
      const x = current.index + t
      const stage = t < 0.5 ? current.stage : next.stage

      waveRows.push({
        x,
        index: Math.round(x),
        stage,
        ...Object.fromEntries(keys.map((key) => [
          key,
          Number((interpolateFlowValue(current[key], next[key], eased, t, keys.indexOf(key))).toFixed(3)),
        ])),
      })
    }
  }

  return waveRows
}

function interpolateFlowValue(start, end, eased, t, keyIndex) {
  const baseValue = start + (end - start) * eased
  const valleyDepth = 0.58 + (keyIndex % 3) * 0.025
  const distanceFromValley = Math.min(1, Math.abs(t - 0.5) * 2)
  const roundedCrest = smootherStep(Math.pow(distanceFromValley, 0.82))
  const roundDip = valleyDepth + (1 - valleyDepth) * roundedCrest

  return Math.max(0, baseValue * roundDip)
}

function smoothStep(value) {
  return value * value * (3 - 2 * value)
}

function smootherStep(value) {
  return value * value * value * (value * (value * 6 - 15) + 10)
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

function resolveSceneIndex(scenes, indexBySequence, sceneOrder, edge) {
  if (indexBySequence.has(sceneOrder)) return indexBySequence.get(sceneOrder)

  const fallbackIndex = edge === 'start'
    ? scenes.findIndex((row) => row.sequence >= sceneOrder)
    : findLastIndex(scenes, (row) => row.sequence <= sceneOrder)

  if (fallbackIndex >= 0) return fallbackIndex
  return edge === 'start' ? 0 : scenes.length - 1
}

function findLastIndex(items, predicate) {
  for (let index = items.length - 1; index >= 0; index -= 1) {
    if (predicate(items[index], index)) return index
  }

  return -1
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

function numberToChinese(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue) || numberValue <= 0) return text(value)

  const digits = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  const integer = Math.floor(numberValue)

  if (integer < 10) return digits[integer]
  if (integer === 10) return '十'
  if (integer < 20) return `十${digits[integer % 10]}`
  if (integer < 100) {
    const tens = Math.floor(integer / 10)
    const ones = integer % 10
    return `${digits[tens]}十${ones ? digits[ones] : ''}`
  }

  return String(integer)
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
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.chart-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  min-height: 30px;
  padding: 0 8px 4px;
}

.chart-toolbar--teleported {
  min-height: 0;
  height: 0;
  padding: 0;
  overflow: visible;
}

.script-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #6b5a4d;
  font-size: 12px;
}

.script-field span {
  font-weight: 700;
}

.script-select {
  width: 116px;
  height: 24px;
  border: 1px solid rgba(120, 84, 62, 0.28);
  border-radius: 4px;
  padding: 0 24px 0 8px;
  color: #4f4036;
  font-size: 12px;
  background: rgba(255, 250, 242, 0.84);
  outline: none;
  cursor: pointer;
}

.script-select:focus {
  border-color: rgba(139, 42, 37, 0.58);
  box-shadow: 0 0 0 2px rgba(139, 42, 37, 0.1);
}

.chart-content {
  display: flex;
  align-items: stretch;
  gap: 5px;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.chart-body {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.river-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.river-svg :deep(.grid-lines line) {
  stroke: rgba(88, 68, 51, 0.1);
  stroke-dasharray: 3 3;
}

.river-svg :deep(.x-axis path),
.river-svg :deep(.y-axis path),
.river-svg :deep(.x-axis line),
.river-svg :deep(.y-axis line) {
  stroke: rgba(88, 68, 51, 0.32);
}

.river-svg :deep(.x-axis text),
.river-svg :deep(.y-axis text),
.river-svg :deep(.axis-title),
.river-svg :deep(.legend text) {
  fill: #67594e;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 11px;
}

.river-svg :deep(.axis-title) {
  font-weight: 700;
}

.river-svg :deep(.legend text) {
  font-size: 12px;
  font-weight: 800;
}

.river-svg :deep(.river-layer) {
  cursor: pointer;
  transition:
    fill-opacity 0.14s ease,
    stroke-width 0.14s ease;
}

.river-svg :deep(.river-current) {
  opacity: 0.82;
  mix-blend-mode: screen;
}

.river-svg :deep(.focus-line) {
  stroke: rgba(73, 56, 47, 0.36);
  stroke-width: 1;
  stroke-dasharray: 4 3;
}

.river-tooltip {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
  width: 200px;
  padding: 8px 9px;
  border: 1px solid rgba(139, 42, 37, 0.22);
  border-radius: 6px;
  color: #49382f;
  font-size: 11px;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  line-height: 1.45;
  background: rgba(255, 250, 242, 0.96);
  box-shadow: 0 8px 20px rgba(73, 56, 47, 0.14);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}

.river-tooltip :deep(.river-tooltip__title) {
  margin-bottom: 3px;
  color: #2f4f63;
  font-weight: 800;
}

.river-tooltip :deep(.river-tooltip__meta) {
  margin-bottom: 2px;
  color: #7a6658;
}

.river-tooltip :deep(.river-tooltip__metric) {
  margin: 5px 0 3px;
  color: #8f2f2a;
  font-weight: 700;
}

.river-tooltip :deep(.river-tooltip__row) {
  display: grid;
  grid-template-columns: 9px 1fr auto;
  gap: 5px;
  align-items: center;
}

.river-tooltip :deep(.river-tooltip__row span) {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.river-tooltip :deep(.river-tooltip__row strong) {
  font-weight: 800;
}

.river-tooltip :deep(.river-tooltip__active) {
  color: #8f2f2a;
}

.chart-state {
  position: absolute;
  inset: 34px 12px 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7a6658;
  font-size: 13px;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  background: rgba(255, 250, 242, 0.72);
}

.chart-state--error {
  color: #8b2a25;
}

.stage-side-panel {
  position: relative;
  display: flex;
  flex: 0 0 clamp(58px, 11%, 76px);
  flex-direction: column;
  gap: 4px;
  min-width: 58px;
  min-height: 0;
  padding: 2px 0;
  overflow: hidden;
}

.stage-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto;
  align-items: center;
  justify-items: center;
  gap: 3px;
  flex: 1 1 0;
  min-height: 0;
  padding: 2px 2px;
  border: 1px solid color-mix(in srgb, var(--stage-color) 46%, transparent);
  border-radius: 4px;
  background: color-mix(in srgb, var(--stage-color) 8%, transparent);
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.34);
  color: #4b3328;
}

.stage-card__name {
  display: grid;
  place-items: center;
  min-width: 0;
  color: var(--stage-color);
  font-size: 14px;
  font-weight: 900;
  line-height: 1.1;
  white-space: nowrap;
}

.stage-card__range {
  min-width: 0;
  color: #3f2b22;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.1;
  text-align: center;
  white-space: nowrap;
}
</style>
