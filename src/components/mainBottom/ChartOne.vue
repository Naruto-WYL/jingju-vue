<template>
  <section class="chart-one-shell historical-bg text-[#4A3B32] font-serif">
    <div class="chart-one-card">
      <div class="chart-one-header">
        <div class="script-select-row">
          <select
            id="scriptSelector"
            v-model="currentScriptKey"
            class="script-selector"
            :disabled="loading || !scriptOptions.length"
            @change="switchScript(currentScriptKey)"
          >
            <option v-if="loading" value="">剧本数据加载中...</option>
            <option v-else-if="!scriptOptions.length" value="">暂无五阶段剧本</option>
            <option v-for="script in scriptOptions" :key="script.key" :value="script.key">
              {{ script.name }}
            </option>
          </select>
          <span id="scriptMeta" class="script-meta">{{ scriptMeta }}</span>
        </div>

        <div class="header-tools">
          <div id="stageContainer" class="stage-container">
            <button
              v-for="stage in currentStages"
              :key="stage"
              type="button"
              class="stage-btn"
              :class="{ active: currentState.stage === stage }"
              :data-stg="stage"
              @click="jumpToStage(stage)"
            >
              {{ stage }}
            </button>
          </div>

          <div class="legend-box">
            <span class="legend-title">图例：</span>
            <div class="legend-item"><span style="background: rgba(0, 76, 126, 0.8);"></span>表演</div>
            <div class="legend-item"><span style="background: rgba(0, 111, 68, 0.8);"></span>活跃</div>
            <div class="legend-item"><span style="background: rgba(160, 82, 45, 0.8);"></span>冲突</div>
            <div class="legend-item"><span style="background: rgba(102, 51, 153, 0.8);"></span>关系</div>
            <div class="legend-item"><span style="background: rgba(178, 34, 34, 0.9);"></span>情绪</div>
            <div class="legend-item"><span style="background: rgba(28, 28, 28, 0.9);"></span>综合</div>
          </div>
        </div>
      </div>

      <div class="chart-one-grid">
        <div id="canvasContainer" ref="canvasContainerRef" class="canvas-container">
          <div class="canvas-title">
            <div id="canvasStageIndicator" class="stage-indicator">{{ currentStageIndicator }}</div>
            <div class="canvas-subtitle">Shan Shui Ink Wash / Auto-tracking Tooltip</div>
          </div>

          <canvas id="analyticalCanvas" ref="canvasRef" class="analytical-canvas"></canvas>

          <div id="cursorTooltip" ref="tooltipRef" class="cursor-tooltip" :class="{ visible: isHovering }">
            <div class="tooltip-title">实时期望张力数值：</div>
            <div class="tooltip-list">
              <div v-for="(metric, index) in tooltipMetrics" :key="metric.label" class="tooltip-row">
                <span :style="{ color: metric.color }">
                  <i :style="{ background: metric.color }"></i>{{ metric.label }}
                </span>
                <strong :id="`val-${index}`" :style="{ color: metric.color }">{{ Math.round(currentState.data[index] || 0) }}%</strong>
              </div>
            </div>
          </div>
        </div>

        <aside class="analysis-panel">
          <h3>剧本节奏与起伏刻画</h3>
          <div class="scene-readout">
            <span>时间轴定位 (X轴)</span>
            <strong id="panel-scene">{{ panelSceneText }}</strong>
          </div>

          <div class="desc-block">
            <span>剧作动力学分析：</span>
            <p id="panel-desc">{{ currentState.desc || '暂无数据' }}</p>
          </div>
        </aside>
      </div>

      <div class="timeline-row">
        <button id="miniPlayBtn" class="mini-play-btn" type="button" @click="togglePlay">
          <svg id="playIcon" class="play-icon" :class="{ hidden: isPlaying }" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
          <svg id="pauseIcon" class="pause-icon" :class="{ hidden: !isPlaying }" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
        </button>
        <div id="progressPercent" class="progress-percent">{{ Math.floor(globalProgress * 100) }}%</div>
        <input
          id="timelineSlider"
          v-model.number="sliderValue"
          class="timeline-slider"
          type="range"
          min="0"
          max="100"
          step="0.01"
          @input="handleSliderChange(sliderValue)"
        />
      </div>

      <div v-if="loading || errorMessage" class="load-state" :class="{ error: errorMessage }">
        {{ errorMessage || '数据加载中...' }}
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as d3 from 'd3'

const CSV_URL = '/数据表合集/4/京剧剧本_1473本_场次剧情动力学_事件增强.csv'
const REQUIRED_STAGES = ['开端', '发展', '转折', '高潮', '结局']
const MAX_SCRIPT_OPTIONS = 80

const streamColorsStroke = [
  'rgba(0, 76, 126, 0.85)',
  'rgba(0, 111, 68, 0.85)',
  'rgba(160, 82, 45, 0.85)',
  'rgba(102, 51, 153, 0.85)',
  'rgba(178, 34, 34, 0.95)',
  'rgba(28, 28, 28, 0.95)',
]
const streamColorsFill = [
  'rgba(0, 76, 126, 0.15)',
  'rgba(0, 111, 68, 0.15)',
  'rgba(160, 82, 45, 0.15)',
  'rgba(102, 51, 153, 0.15)',
  'rgba(178, 34, 34, 0.20)',
  'rgba(28, 28, 28, 0.15)',
]

const tooltipMetrics = [
  { label: '表演形式密度', color: '#004C7E' },
  { label: '角色活跃度', color: '#006F44' },
  { label: '冲突强度', color: '#A0522D' },
  { label: '关系变化强度', color: '#663399' },
  { label: '情绪强度', color: '#B22222' },
  { label: '综合剧情强度', color: '#1C1C1C' },
]

const canvasRef = ref(null)
const canvasContainerRef = ref(null)
const tooltipRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const allScripts = ref({})
const scriptOptions = ref([])
const currentScriptKey = ref('')
const currentStages = ref(REQUIRED_STAGES)
const currentState = ref({
  data: [0, 0, 0, 0, 0, 0],
  speed: 0.01,
  turb: 2,
  stage: '加载中',
  conflict: '',
  desc: '暂无数据',
  leftLabel: '-',
  rightLabel: '-',
})
const globalProgress = ref(0)
const sliderValue = ref(0)
const isPlaying = ref(false)
const isHovering = ref(false)

let ctx = null
let flowTime = 0
let trackerXCss = 0
let currentMouseY = 0
let animationFrameId = 0
let resizeHandler = null
let physics = { visibleRatio: 0.2 }
const layout = { paddingLeft: 60, paddingRight: 40, paddingTop: 85, paddingBottom: 40 }

const currentScript = computed(() => allScripts.value[currentScriptKey.value] || null)
const scriptMeta = computed(() => currentScript.value?.meta || '-')
const currentStageIndicator = computed(() => `${currentState.value.stage || '-'} · ${currentState.value.conflict || '-'}`)
const panelSceneText = computed(() => {
  if (!currentScript.value) return '-'
  return globalProgress.value >= 1
    ? `气韵定格：${currentState.value.rightLabel}`
    : `气韵逼近 ${currentState.value.rightLabel}`
})

onMounted(async () => {
  await loadCsvScripts()
  await nextTick()
  initCanvas()
  attachHoverEvents()
  if (currentScriptKey.value) switchScript(currentScriptKey.value)
  animate()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

async function loadCsvScripts() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch(CSV_URL)
    if (!response.ok) throw new Error(`CSV 加载失败：${response.status}`)
    const text = (await response.text()).replace(/^\uFEFF/, '')
    const rows = d3.csvParse(text).map(normalizeRow).filter((row) => row.scriptId && row.scriptName)
    const scripts = buildScriptsFromRows(rows)
    allScripts.value = scripts
    scriptOptions.value = Object.values(scripts)
      .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, 'zh-Hans-CN'))
      .slice(0, MAX_SCRIPT_OPTIONS)
      .map((script) => ({ key: script.key, name: `${script.name}（${script.sourceSceneCount}场）` }))
    currentScriptKey.value = scriptOptions.value[0]?.key || ''
    if (!currentScriptKey.value) errorMessage.value = 'CSV 中未筛选到包含开端、发展、转折、高潮、结局的剧本。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'CSV 加载失败'
  } finally {
    loading.value = false
  }
}

function normalizeRow(row) {
  return {
    scriptId: row['剧本编号']?.trim() || '',
    scriptName: row['剧本名字']?.trim() || '',
    sequence: Number(row['场次序号'] || 0),
    sceneName: row['场次名称']?.trim() || '',
    stage: row['所属阶段']?.trim() || '',
    conflict: row['冲突类型']?.trim() || '',
    performance: Number(row['表演形式密度(%)'] || 0),
    role: Number(row['角色活跃度(%)'] || 0),
    conflictStrength: Number(row['冲突强度(%)'] || 0),
    relation: Number(row['关系变化强度(%)'] || 0),
    emotion: Number(row['情绪强度(%)'] || 0),
    overall: Number(row['综合剧情强度(%)'] || 0),
    speed: Number(row['基准流速'] || 0.01),
    turb: Number(row['湍流震荡值'] || 2),
    desc: row['剧作动力学分析']?.trim() || '',
  }
}

function buildScriptsFromRows(rows) {
  const grouped = d3.group(rows, (row) => `${row.scriptId}__${row.scriptName}`)
  const candidates = []

  for (const [key, groupRows] of grouped.entries()) {
    const scenes = groupRows.sort((a, b) => a.sequence - b.sequence).map((row) => ({ ...row }))
    deriveTurnStage(scenes)
    const stageSet = new Set(scenes.map((scene) => scene.stage))
    if (!REQUIRED_STAGES.every((stage) => stageSet.has(stage))) continue
    if (!hasMeaningfulConflictVariation(scenes)) continue

    const displayScenes = selectDisplayScenes(scenes)
    if (displayScenes.length < 5 || displayScenes.length > 8) continue
    if (!REQUIRED_STAGES.every((stage) => new Set(displayScenes.map((scene) => scene.stage)).has(stage))) continue

    const script = {
      key,
      name: scenes[0].scriptName,
      scriptId: scenes[0].scriptId,
      sourceSceneCount: scenes.length,
      score: scoreScript(scenes, displayScenes),
      meta: `京剧剧本 ${scenes[0].scriptId} / 优选五阶段剧情动力学`,
      stages: REQUIRED_STAGES,
      axisXLabels: displayScenes.map((scene) => scene.sceneName || `第${scene.sequence + 1}场`),
      scenes: displayScenes.map((scene, index) => ({
        xIdx: index,
        label: scene.sceneName || `第${scene.sequence + 1}场`,
        stage: scene.stage,
        conflict: scene.conflict,
        data: [scene.performance, scene.role, scene.conflictStrength, scene.relation, scene.emotion, scene.overall],
        speed: Math.max(0.01, Math.min(0.18, scene.speed || 0.01)),
        turb: Math.max(2, Math.min(150, scene.turb || 2)),
        desc: scene.desc,
      })),
    }
    candidates.push(script)
  }

  const bestByName = new Map()
  for (const script of candidates) {
    const current = bestByName.get(script.name)
    if (!current || script.score > current.score) {
      bestByName.set(script.name, script)
    }
  }

  return Object.fromEntries(Array.from(bestByName.values()).map((script) => [script.key, script]))
}

function deriveTurnStage(scenes) {
  const firstClimaxIndex = scenes.findIndex((scene) => scene.stage === '高潮')
  if (firstClimaxIndex <= 0) return
  const developmentBeforeClimax = scenes
    .map((scene, index) => ({ scene, index }))
    .filter((item) => item.scene.stage === '发展' && item.index < firstClimaxIndex)
  if (developmentBeforeClimax.length < 2) return

  const turnItem = developmentBeforeClimax[developmentBeforeClimax.length - 1]
  turnItem.scene.stage = '转折'
  if (!turnItem.scene.conflict || turnItem.scene.conflict === '压抑铺垫') {
    turnItem.scene.conflict = '转折突变'
  }
  turnItem.scene.desc = turnItem.scene.desc.replace(/^发展阶段/, '转折阶段')
}

function hasMeaningfulConflictVariation(scenes) {
  const stageConflict = new Map()
  for (const stage of REQUIRED_STAGES) {
    const stageScenes = scenes.filter((scene) => scene.stage === stage)
    if (!stageScenes.length) return false
    const topConflict = d3.rollups(
      stageScenes,
      (items) => items.length,
      (scene) => scene.conflict,
    ).sort((a, b) => b[1] - a[1])[0]?.[0]
    stageConflict.set(stage, topConflict)
  }
  return new Set(stageConflict.values()).size >= 3
}

function selectDisplayScenes(scenes) {
  const selected = []
  const add = (scene) => {
    if (scene && !selected.includes(scene)) selected.push(scene)
  }

  const byStage = (stage) => scenes.filter((scene) => scene.stage === stage)
  const strongest = (items) => [...items].sort((a, b) => b.overall - a.overall || b.turb - a.turb)[0]

  add(byStage('开端')[0])

  const development = byStage('发展')
  if (development.length > 1) {
    add(development[0])
    add(strongest(development.slice(1)))
  } else {
    add(development[0])
  }

  add(strongest(byStage('转折')))

  const climaxes = byStage('高潮')
  add(strongest(climaxes))
  const extraClimax = climaxes
    .filter((scene) => !selected.includes(scene))
    .sort((a, b) => b.turb - a.turb || b.overall - a.overall)[0]
  if (extraClimax && selected.length < 7) add(extraClimax)

  add(byStage('结局').at(-1))

  return selected
    .filter(Boolean)
    .sort((a, b) => a.sequence - b.sequence)
    .filter((scene, index, arr) => index === 0 || scene.sequence !== arr[index - 1].sequence)
}

function scoreScript(scenes, displayScenes) {
  const conflicts = new Set(scenes.map((scene) => scene.conflict)).size
  const stageConflicts = new Set(displayScenes.map((scene) => `${scene.stage}:${scene.conflict}`)).size
  const avgOverall = d3.mean(displayScenes, (scene) => scene.overall) || 0
  const avgTurb = d3.mean(displayScenes, (scene) => scene.turb) || 0
  const sceneCountFit = Math.max(0, 20 - Math.abs(displayScenes.length - 7) * 5)
  const sourceCountFit = Math.max(0, 16 - Math.abs(scenes.length - 8))
  return conflicts * 12 + stageConflicts * 9 + avgOverall * 0.65 + avgTurb * 0.22 + sceneCountFit + sourceCountFit
}

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  resizeHandler = resizeCanvas
  window.addEventListener('resize', resizeHandler)
  resizeCanvas()
}

function attachHoverEvents() {
  const container = canvasContainerRef.value
  const tooltip = tooltipRef.value
  if (!container || !tooltip) return

  container.addEventListener('mouseenter', () => {
    isHovering.value = true
  })
  container.addEventListener('mousemove', (event) => {
    const rect = container.getBoundingClientRect()
    currentMouseY = event.clientY - rect.top
    isHovering.value = true
  })
  container.addEventListener('mouseleave', () => {
    isHovering.value = false
  })
}

function resizeCanvas() {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !ctx) return
  const rect = container.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.round(rect.width * ratio)
  canvas.height = Math.round(rect.height * ratio)
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
}

function getInterpolatedState(progress) {
  const script = currentScript.value
  if (!script?.scenes?.length) return currentState.value

  const numScenes = script.scenes.length
  const floatIndex = progress * (numScenes - 1)
  const leftIdx = Math.min(Math.floor(floatIndex), numScenes - 1)
  const rightIdx = Math.min(leftIdx + 1, numScenes - 1)
  const t = floatIndex - leftIdx
  const smoothT = t * t * (3 - 2 * t)
  const leftScene = script.scenes[leftIdx]
  const rightScene = script.scenes[rightIdx]
  const state = {
    data: [],
    speed: leftScene.speed + (rightScene.speed - leftScene.speed) * smoothT,
    turb: leftScene.turb + (rightScene.turb - leftScene.turb) * smoothT,
    stage: t < 0.5 ? leftScene.stage : rightScene.stage,
    conflict: t < 0.5 ? leftScene.conflict : rightScene.conflict,
    desc: t < 0.5 ? leftScene.desc : rightScene.desc,
    leftLabel: leftScene.label,
    rightLabel: rightScene.label,
  }

  for (let i = 0; i < 6; i += 1) {
    state.data.push(leftScene.data[i] + (rightScene.data[i] - leftScene.data[i]) * smoothT)
  }
  return state
}

function animate() {
  if (isPlaying.value) {
    globalProgress.value += 0.00055
    if (globalProgress.value >= 1) {
      globalProgress.value = 0
      sliderValue.value = 0
      physics.visibleRatio = 0.2
      flowTime = 0
      isPlaying.value = false
      syncUIFromProgress(false)
    } else {
      syncUIFromProgress(false)
    }
  }

  drawCanvas()
  animationFrameId = requestAnimationFrame(animate)
}

function drawCanvas() {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !ctx || !currentScript.value) return

  const state = getInterpolatedState(globalProgress.value)
  currentState.value = state
  flowTime += state.speed

  let targetVisibleRatio = Math.max(0.2, globalProgress.value / 0.85)
  if (targetVisibleRatio > 1) targetVisibleRatio = 1
  physics.visibleRatio += (targetVisibleRatio - physics.visibleRatio) * 0.15

  const ratio = window.devicePixelRatio || 1
  const rect = container.getBoundingClientRect()
  if (canvas.width !== Math.round(rect.width * ratio) || canvas.height !== Math.round(rect.height * ratio)) {
    resizeCanvas()
  }

  const w = canvas.width / ratio
  const h = canvas.height / ratio
  layout.paddingTop = h < 190 ? 34 : h < 280 ? 42 : h < 360 ? 54 : 78
  layout.paddingBottom = h < 190 ? 22 : h < 280 ? 26 : h < 360 ? 32 : 40
  layout.paddingLeft = w < 520 ? 34 : w < 760 ? 42 : 58
  layout.paddingRight = w < 520 ? 16 : w < 760 ? 24 : 36
  const graphW = Math.max(1, w - layout.paddingLeft - layout.paddingRight)
  const graphH = Math.max(1, h - layout.paddingTop - layout.paddingBottom)
  const baseY = h - layout.paddingBottom

  ctx.fillStyle = '#FDFBF7'
  ctx.fillRect(0, 0, w, h)

  drawYAxis(w, graphH, baseY)
  drawXAxis(w, graphW, baseY)
  drawWaves(graphW, graphH, baseY, state)
  drawTracker(baseY)
  syncTooltipPosition()
}

function drawYAxis(w, graphH, baseY) {
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  ctx.font = '10px sans-serif'
  ctx.lineWidth = 1
  ;[25, 50, 75, 100].forEach((value) => {
    const y = baseY - (value * graphH) / 100
    ctx.strokeStyle = 'rgba(160, 82, 45, 0.05)'
    ctx.beginPath()
    ctx.moveTo(layout.paddingLeft, y)
    ctx.lineTo(w - layout.paddingRight, y)
    ctx.stroke()
    ctx.fillStyle = '#A69482'
    ctx.fillText(`${value}%`, layout.paddingLeft - 10, y)
  })
}

function drawXAxis(w, graphW, baseY) {
  const script = currentScript.value
  const labels = script.axisXLabels
  const numScenes = labels.length
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'

  labels.forEach((label, index) => {
    const ratio = index / Math.max(1, numScenes - 1)
    if (ratio <= physics.visibleRatio + 0.05) {
      const x = layout.paddingLeft + (ratio / physics.visibleRatio) * graphW
      ctx.strokeStyle = 'rgba(28, 28, 28, 0.15)'
      ctx.beginPath()
      ctx.moveTo(x, baseY)
      ctx.lineTo(x, baseY + 6)
      ctx.stroke()

      const isActive = Math.abs(ratio - globalProgress.value) <= 0.5 / Math.max(1, numScenes - 1)
      ctx.fillStyle = isActive ? '#B22222' : '#998370'
      ctx.font = isActive ? 'bold 11px sans-serif' : '10px sans-serif'
      ctx.fillText(label, x, baseY + 14)
    }
  })

  ctx.strokeStyle = '#D9CEBF'
  ctx.beginPath()
  ctx.moveTo(layout.paddingLeft, baseY)
  ctx.lineTo(w - layout.paddingRight, baseY)
  ctx.stroke()
}

function drawWaves(graphW, graphH, baseY, state) {
  const script = currentScript.value
  const numScenes = script.scenes.length
  const currentTrackerX = layout.paddingLeft + (globalProgress.value / physics.visibleRatio) * graphW
  trackerXCss = currentTrackerX

  for (let streamIndex = 0; streamIndex < 6; streamIndex += 1) {
    const wavePoints = []

    for (let xPixel = layout.paddingLeft; xPixel <= currentTrackerX; xPixel += 1) {
      const pixelRatio = (xPixel - layout.paddingLeft) / graphW
      const relativeX = pixelRatio * physics.visibleRatio
      let interpolatedValue = 0

      for (let sceneIndex = 0; sceneIndex < numScenes - 1; sceneIndex += 1) {
        const leftRatio = sceneIndex / (numScenes - 1)
        const rightRatio = (sceneIndex + 1) / (numScenes - 1)
        if (relativeX >= leftRatio && relativeX <= rightRatio) {
          const t = (relativeX - leftRatio) / (rightRatio - leftRatio)
          const smoothT = t * t * (3 - 2 * t)
          const leftValue = script.scenes[sceneIndex].data[streamIndex]
          const rightValue = script.scenes[sceneIndex + 1].data[streamIndex]
          interpolatedValue = leftValue + (rightValue - leftValue) * smoothT
          break
        }
      }

      const waveFreq = 0.04 + state.turb * 0.0004
      const dynamicRipple = Math.sin(xPixel * waveFreq - flowTime * 2.5 + streamIndex * 7) * (state.turb * 0.18) * (interpolatedValue / 100)
      const finalY = Math.min(baseY, baseY - (interpolatedValue * graphH) / 100 + dynamicRipple)
      wavePoints.push({ x: xPixel, y: finalY })
    }

    if (!wavePoints.length) continue
    ctx.beginPath()
    ctx.moveTo(layout.paddingLeft, baseY)
    wavePoints.forEach((point) => ctx.lineTo(point.x, point.y))
    ctx.lineTo(currentTrackerX, baseY)
    ctx.closePath()
    ctx.fillStyle = streamColorsFill[streamIndex]
    ctx.fill()

    ctx.beginPath()
    wavePoints.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y)
      else ctx.lineTo(point.x, point.y)
    })
    ctx.strokeStyle = streamColorsStroke[streamIndex]
    ctx.lineWidth = 2.2
    ctx.stroke()

    const lastPoint = wavePoints[wavePoints.length - 1]
    ctx.beginPath()
    ctx.arc(lastPoint.x, lastPoint.y, 2.5, 0, Math.PI * 2)
    ctx.fillStyle = streamColorsStroke[streamIndex]
    ctx.fill()
  }
}

function drawTracker(baseY) {
  ctx.strokeStyle = isHovering.value ? 'rgba(160, 82, 45, 0.9)' : 'rgba(160, 82, 45, 0.4)'
  ctx.lineWidth = isHovering.value ? 2.5 : 1.5
  ctx.setLineDash(isHovering.value ? [] : [4, 4])
  ctx.beginPath()
  ctx.moveTo(trackerXCss, layout.paddingTop)
  ctx.lineTo(trackerXCss, baseY)
  ctx.stroke()
  ctx.setLineDash([])
}

function syncTooltipPosition() {
  const container = canvasContainerRef.value
  const tooltip = tooltipRef.value
  if (!container || !tooltip || !isHovering.value) return
  const rect = container.getBoundingClientRect()
  let leftPos = trackerXCss + 15
  if (leftPos + 220 > rect.width) leftPos = trackerXCss - 225
  tooltip.style.left = `${leftPos}px`
  tooltip.style.top = `${Math.max(20, Math.min(currentMouseY - 40, rect.height - 220))}px`
}

function syncUIFromProgress(isDragging = false) {
  currentState.value = getInterpolatedState(globalProgress.value)
  if (!isDragging) sliderValue.value = globalProgress.value * 100
}

function switchScript(key) {
  if (isPlaying.value) togglePlay()
  currentScriptKey.value = key
  currentStages.value = currentScript.value?.stages || REQUIRED_STAGES
  globalProgress.value = 0
  sliderValue.value = 0
  physics.visibleRatio = 0.2
  flowTime = 0
  syncUIFromProgress()
}

function handleSliderChange(value) {
  if (isPlaying.value) togglePlay()
  globalProgress.value = Number(value) / 100
  syncUIFromProgress(true)
}

function jumpToStage(stage) {
  const script = currentScript.value
  if (!script) return
  const stageIndex = script.scenes.findIndex((scene) => scene.stage === stage)
  if (stageIndex < 0) return
  jumpToProgress(stageIndex / Math.max(1, script.scenes.length - 1))
}

function jumpToProgress(targetProgress) {
  if (isPlaying.value) togglePlay()
  globalProgress.value = targetProgress
  sliderValue.value = targetProgress * 100
  syncUIFromProgress()
}

function togglePlay() {
  if (!isPlaying.value && globalProgress.value >= 1) {
    globalProgress.value = 0
    sliderValue.value = 0
    physics.visibleRatio = 0.2
  }
  isPlaying.value = !isPlaying.value
}
</script>

<style scoped>
.chart-one-shell {
  height: 100%;
  min-height: 0;
  width: 100%;
  padding: 0;
  color: #4a3b32;
  box-sizing: border-box;
}

.chart-one-shell * {
  box-sizing: border-box;
}

.historical-bg {
  background-color: #f8f2e9;
  background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAIklEQVQIW2NkQAKrVq36z8gAFWNhYGFkYMSsB8wEVwMzA5sfsjgAs44RAnE094QAAAAASUVORK5CYII=');
}

.chart-one-card {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  padding: clamp(4px, 0.55vw, 8px);
  background: #fdfbf7;
  box-shadow: 0 6px 18px rgba(70, 51, 35, 0.1);
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 4px;
}

.chart-one-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  min-width: 0;
  min-height: 0;
  margin-bottom: 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #d9cebf;
}

.script-select-row,
.header-tools,
.legend-box,
.legend-item,
.timeline-row {
  display: flex;
  align-items: center;
}

.script-select-row {
  flex: 0 1 180px;
  gap: 4px;
  min-width: 0;
  max-width: 100%;
}

.script-selector {
  width: min(118px, 58%);
  min-width: 96px;
  border: 1px solid #cfc0b0;
  border-radius: 5px;
  padding: 2px 6px;
  background: transparent;
  color: #b22222;
  font-size: 12px;
  font-weight: 700;
  outline: none;
  cursor: pointer;
}

.script-meta {
  border: 1px solid #d9cebf;
  border-radius: 4px;
  padding: 1px 5px;
  background: #fff;
  color: #998370;
  font-size: 9px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-tools {
  flex: 1 1 auto;
  flex-wrap: nowrap;
  justify-content: flex-end;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.stage-container {
  display: flex;
  flex: 0 0 auto;
  gap: 1px;
  border: 1px solid #d9cebf;
  border-radius: 5px;
  padding: 1px;
  background: #fff;
}

.stage-btn {
  border: 0;
  border-radius: 5px;
  padding: 2px 4px;
  background: #f5efe6;
  color: #4a3b32;
  font-size: 10px;
  line-height: 1.2;
  cursor: pointer;
  transition: 0.16s ease;
}

.stage-btn.active,
.stage-btn:hover {
  background: #b22222;
  color: #fff;
}

.legend-box {
  flex: 0 1 auto;
  flex-wrap: nowrap;
  justify-content: flex-end;
  gap: 3px 5px;
  min-width: 0;
  border: 1px solid #d9cebf;
  border-radius: 6px;
  padding: 2px 5px;
  background: #fff;
  box-shadow: inset 0 1px 3px rgba(70, 51, 35, 0.06);
  font-size: 9px;
  line-height: 1.15;
}

.legend-title {
  margin-right: 1px;
  color: #998370;
  font-weight: 700;
  white-space: nowrap;
}

.legend-item {
  white-space: nowrap;
}

.legend-item span {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
  margin-right: 2px;
}

.chart-one-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(160px, 0.34fr);
  gap: 6px;
  width: 100%;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.canvas-container {
  position: relative;
  min-width: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #e6dcd3;
  border-radius: 8px;
  background: #fdfbf7;
  box-shadow: inset 0 2px 10px rgba(70, 51, 35, 0.04);
}

.canvas-title {
  position: absolute;
  z-index: 2;
  top: 5px;
  left: 12px;
  right: 8px;
  pointer-events: none;
}

.stage-indicator {
  color: #b22222;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-subtitle {
  margin-top: 1px;
  color: #a69482;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 8px;
}

.analytical-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.cursor-tooltip {
  position: absolute;
  z-index: 5;
  width: 190px;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  padding: 10px;
  background: rgba(253, 251, 247, 0.95);
  box-shadow: 0 10px 24px rgba(70, 51, 35, 0.16);
  opacity: 0;
  pointer-events: none;
  backdrop-filter: blur(5px);
  transition: opacity 0.2s ease-out;
}

.cursor-tooltip.visible {
  opacity: 1;
}

.tooltip-title {
  margin-bottom: 6px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e6dcd3;
  color: #a0522d;
  font-size: 11px;
  font-weight: 700;
}

.tooltip-list {
  display: grid;
  gap: 6px;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.tooltip-row span {
  display: flex;
  align-items: center;
}

.tooltip-row i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

.tooltip-row strong {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
}

.analysis-panel {
  min-width: 0;
  min-height: 0;
  height: 100%;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  padding: 6px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(70, 51, 35, 0.05);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.analysis-panel h3 {
  margin: 0 0 5px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e6dcd3;
  color: #b22222;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.18;
}

.scene-readout {
  margin-bottom: 5px;
}

.scene-readout span {
  display: block;
  margin-bottom: 2px;
  color: #998370;
  font-size: 9px;
}

.scene-readout strong {
  display: block;
  color: #4a3b32;
  font-size: 11px;
  line-height: 1.2;
}

.desc-block span {
  display: block;
  margin-bottom: 2px;
  color: #a0522d;
  font-size: 9px;
  font-weight: 700;
}

.desc-block {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.desc-block p {
  flex: 1 1 auto;
  height: auto;
  margin: 0;
  min-height: 0;
  padding-right: 4px;
  overflow-y: auto;
  overflow-x: hidden;
  color: #5c4636;
  font-size: 9.5px;
  line-height: 1.34;
  text-align: justify;
}

.timeline-row {
  gap: 6px;
  width: 100%;
  min-width: 0;
  min-height: 28px;
  margin-top: 0;
  border: 1px solid #d9cebf;
  border-radius: 7px;
  padding: 3px 8px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(70, 51, 35, 0.05);
}

.mini-play-btn {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: 999px;
  background: #a0522d;
  color: #fff;
  box-shadow: 0 4px 10px rgba(160, 82, 45, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.16s ease;
}

.mini-play-btn:hover {
  background: #8b4513;
}

.mini-play-btn svg {
  width: 12px;
  height: 12px;
  fill: currentColor;
}

.play-icon {
  margin-left: 2px;
}

.hidden {
  display: none;
}

.progress-percent {
  width: 40px;
  padding-right: 4px;
  color: #b22222;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.timeline-slider {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #e6dcd3;
  appearance: none;
  cursor: pointer;
}

.timeline-slider::-webkit-slider-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #a0522d;
  box-shadow: 0 0 6px rgba(160, 82, 45, 0.4);
  appearance: none;
  cursor: pointer;
  transition: transform 0.1s;
}

.timeline-slider::-webkit-slider-thumb:hover {
  transform: scale(1.3);
}

.load-state {
  position: absolute;
  inset: auto 20px 78px 20px;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  padding: 10px 12px;
  background: rgba(253, 251, 247, 0.92);
  color: #a0522d;
  font-size: 13px;
  text-align: center;
}

.load-state.error {
  color: #b22222;
}

:global(.single-preview-panel--main-bottom) .chart-one-shell {
  height: 100%;
  min-height: 0;
  padding: 0;
}

:global(.single-preview-panel--main-bottom) .chart-one-card {
  height: 100%;
  min-height: 0;
  padding: clamp(6px, 0.8vw, 12px);
  gap: clamp(4px, 0.5vw, 8px);
}

:global(.single-preview-panel--main-bottom) .chart-one-header {
  gap: 10px;
  padding-bottom: 6px;
}

:global(.single-preview-panel--main-bottom) .script-select-row {
  gap: 6px;
  min-width: 0;
}

:global(.single-preview-panel--main-bottom) .script-selector {
  width: min(220px, 52%);
  max-width: 220px;
  padding: 3px 7px;
  font-size: 14px;
}

:global(.single-preview-panel--main-bottom) .script-meta {
  font-size: 10px;
}

:global(.single-preview-panel--main-bottom) .header-tools {
  gap: 6px;
}

:global(.single-preview-panel--main-bottom) .stage-container {
  padding: 2px;
}

:global(.single-preview-panel--main-bottom) .stage-btn {
  padding: 3px 8px;
  font-size: 11px;
}

:global(.single-preview-panel--main-bottom) .legend-box {
  gap: 4px 8px;
  padding: 3px 7px;
  font-size: 10px;
}

:global(.single-preview-panel--main-bottom) .chart-one-grid {
  grid-template-columns: minmax(0, 1fr) minmax(190px, 0.34fr);
  gap: 8px;
  min-height: 0;
}

:global(.single-preview-panel--main-bottom) .canvas-container {
  height: 100%;
  min-height: 0;
}

:global(.single-preview-panel--main-bottom) .canvas-title {
  top: 6px;
  left: 14px;
}

:global(.single-preview-panel--main-bottom) .stage-indicator {
  font-size: 15px;
}

:global(.single-preview-panel--main-bottom) .canvas-subtitle {
  margin-top: 2px;
  font-size: 9px;
}

:global(.single-preview-panel--main-bottom) .analysis-panel {
  min-height: 0;
  padding: 8px;
}

:global(.single-preview-panel--main-bottom) .analysis-panel h3 {
  margin-bottom: 6px;
  padding-bottom: 5px;
  font-size: 13px;
}

:global(.single-preview-panel--main-bottom) .scene-readout {
  margin-bottom: 7px;
}

:global(.single-preview-panel--main-bottom) .scene-readout span {
  font-size: 10px;
}

:global(.single-preview-panel--main-bottom) .scene-readout strong {
  font-size: 13px;
}

:global(.single-preview-panel--main-bottom) .desc-block span {
  margin-bottom: 4px;
  font-size: 10px;
}

:global(.single-preview-panel--main-bottom) .desc-block p {
  height: auto;
  overflow-y: auto;
  font-size: 11px;
  line-height: 1.42;
}

:global(.single-preview-panel--main-bottom) .timeline-row {
  gap: 8px;
  padding: 4px 10px;
}

:global(.single-preview-panel--main-bottom) .mini-play-btn {
  width: 26px;
  height: 26px;
}

:global(.single-preview-panel--main-bottom) .mini-play-btn svg {
  width: 14px;
  height: 14px;
}

::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-thumb {
  background: #d9cebf;
  border-radius: 2px;
}

@media (max-width: 1100px) and (min-width: 641px) {
  .chart-one-card {
    padding: 4px;
  }

  .chart-one-header {
    gap: 4px;
    overflow: hidden;
  }

  .script-select-row {
    flex: 0 1 118px;
  }

  .script-selector {
    width: 100%;
    min-width: 0;
    font-size: 11px;
  }

  .script-meta,
  .legend-title {
    display: none;
  }

  .header-tools {
    gap: 3px;
    overflow: hidden;
  }

  .stage-btn {
    padding: 2px 3px;
    font-size: 9px;
  }

  .legend-box {
    gap: 2px 4px;
    padding: 2px 4px;
    font-size: 8.5px;
  }

  .legend-item span {
    width: 7px;
    height: 7px;
  }

  .chart-one-grid {
    grid-template-columns: minmax(0, 1fr) minmax(140px, 0.32fr);
  }
}

@media (max-width: 640px) {
  .chart-one-header,
  .chart-one-grid {
    grid-template-columns: 1fr;
  }

  .chart-one-header {
    flex-direction: column;
  }

  .header-tools {
    justify-content: flex-start;
  }

  .chart-one-grid {
    display: block;
  }

  .analysis-panel {
    min-height: 0;
    margin-top: 16px;
  }
}
</style>
