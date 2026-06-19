<template>
  <section class="qiyun-view">
    <div class="qiyun-card">
      <div class="qiyun-topbar">
        <div class="selector-group">
          <label class="select-box stage-count-box">
            <select v-model="stageCountFilter" :disabled="loading" @change="filterByStageCount(stageCountFilter)">
              <option v-for="count in stageCountOptions" :key="count" :value="String(count)">
                {{ stageCountLabel(count) }}（{{ stageBuckets[count]?.length || 0 }}本）
              </option>
            </select>
          </label>

          <label class="select-box script-box">
            <PlaySelect
              v-model="currentScriptKey"
              :options="scriptSelectOptions"
              :max-visible="5"
              :placeholder="loading ? '加载剧本数据...' : '请选择剧本'"
              :disabled="loading || !scriptOptions.length"
              @change="switchScript"
            />
          </label>
        </div>

        <div class="stage-container">
          <button
            v-for="stage in currentStages"
            :key="stage"
            type="button"
            class="stage-btn"
            :class="{ active: currentState.stage === stage || currentState.stage?.includes(stage) }"
            @click="jumpToStage(stage)"
          >
            {{ stage }}
          </button>
        </div>

        <div class="qiyun-legend">
          <span class="legend-title">图例：</span>
          <div class="legend-list">
            <span v-for="(name, index) in streamColorNames" :key="name" class="legend-item">
              <i :style="{ background: streamColorsStroke[index] }"></i>{{ compactLegendName(name, index) }}
            </span>
          </div>
          <button
            type="button"
            class="analysis-toggle"
            :class="{ active: analysisOpen }"
            :aria-expanded="analysisOpen"
            @click.stop="analysisOpen = !analysisOpen"
          >
            说明
          </button>
        </div>
      </div>

      <div class="qiyun-main">
        <div
          ref="canvasPanelRef"
          class="canvas-panel"
          @mousemove="handleCanvasMouseMove"
          @mouseleave="handleCanvasMouseLeave"
          @click="handleCanvasClick"
        >
          <div class="canvas-heading">
            <span>{{ currentStageIndicator }}</span>
          </div>
          <canvas ref="canvasRef" class="analytical-canvas" :class="{ clickable: hoveringAnchor }"></canvas>

          <div ref="tooltipRef" class="cursor-tooltip" :class="{ visible: isHovering }">
            <div class="tooltip-title">实时期望张力数值：</div>
            <div class="tooltip-grid">
              <div v-for="(name, index) in streamColorNames" :key="name" class="tooltip-row">
                <span :style="{ color: streamColorsStroke[index] }">{{ name }}</span>
                <strong :style="{ color: streamColorsStroke[index] }">{{ Math.round(currentState.data[index] || 0) }}%</strong>
              </div>
            </div>
          </div>
        </div>

        <div v-if="analysisOpen" class="analysis-backdrop" @click="analysisOpen = false"></div>
        <aside class="analysis-panel" :class="{ open: analysisOpen }">
          <div class="panel-title-row">
            <strong>{{ lockedScene ? '叙事主题结构拆解' : '剧本节奏与起伏刻画' }}</strong>
            <button type="button" class="info-btn" @click.stop="infoOpen = !infoOpen">?</button>
            <button type="button" class="panel-close-btn" @click.stop="analysisOpen = false">关闭</button>
            <div class="info-tooltip" :class="{ visible: infoOpen }">
              <b>系统数据量化溯源说明</b>
              <span>表演/活跃基于剧本动作提示语频次与同场角色网络密度计算。</span>
              <span>冲突/情绪结合情感词典提取对抗张力极性。</span>
              <span>综合强度由六维加权移动平均形成总体包络线。</span>
            </div>
          </div>

          <div v-if="!lockedScene" class="scene-loc-box">
            <span>时间轴定位：</span>
            <b>{{ panelSceneText }}</b>
          </div>

          <div class="desc-block">
            <span class="desc-title">{{ lockedScene ? `锁定锚点：【${lockedScene.theme}】` : '本场剧作动力学分析：' }}</span>

            <template v-if="lockedScene">
              <div class="locked-inline-summary">
                <span><small>场次</small><b>{{ lockedScene.label }}</b></span>
                <span><small>阶段</small><b>{{ lockedScene.stage }}</b></span>
                <span><small>主题</small><b>{{ lockedScene.theme }}</b></span>
                <span v-for="row in lockedMetricRows" :key="row.label">
                  <small>{{ row.label }}</small>
                  <b :style="{ color: row.color }">{{ row.value }}%</b>
                </span>
                <span>
                  <small>综合剧情</small>
                  <b>{{ Math.round(lockedScene.data[5]) }}%</b>
                </span>
                <span>
                  <small>基准流速</small>
                  <b>{{ lockedScene.speed }}</b>
                </span>
                <span>
                  <small>湍流震荡</small>
                  <b>{{ Math.round(lockedScene.turb) }}</b>
                </span>
              </div>
              <p class="locked-insight"><b>【学术提炼】</b>{{ lockedInsight }}<br />{{ lockedScene.desc }}</p>
            </template>

            <p v-else class="normal-desc">
              <small>单剧本推演：以场次为轴，观察阶段主题变化驱动的六维张力演进。</small>
              {{ currentState.desc || '暂无数据' }}
            </p>
          </div>

          <div v-if="!lockedScene" class="hover-hint">
            点击图表白底圆点开启联动穿透
          </div>
        </aside>
      </div>

      <div v-if="loading || errorMessage" class="load-state" :class="{ error: errorMessage }">
        {{ errorMessage || '数据加载中...' }}
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PlaySelect from '../PlaySelect.vue'
import { findScriptKeyByPlay, loadQiyunDataset, sceneNoFromSceneId, stageCountLabel } from './qiyunData'
import { streamColorNames, streamColorsStroke } from './qiyunData'
import { linkageState, loadLinkageData } from '../../services/linkageStore'
import { FEATURED_PLAY_TITLES, pinFeaturedPlays } from '../../services/playCatalog'

const canvasPanelRef = ref(null)
const canvasRef = ref(null)
const tooltipRef = ref(null)
const radarCanvasRef = ref(null)

const loading = ref(true)
const errorMessage = ref('')
const scripts = ref({})
const stageBuckets = ref({})
const stageCountFilter = ref('')
const currentScriptKey = ref('')
const currentState = ref(makeEmptyState())
const globalProgress = ref(0)
const isHovering = ref(false)
const hoveringAnchor = ref(false)
const lockedScene = ref(null)
const infoOpen = ref(false)
const analysisOpen = ref(false)

let ctx = null
let animationFrameId = 0
let trackerXCss = 0
let currentMouseY = 0
let activeAnchors = []
let resizeHandler = null
let needsDraw = true
let physics = { visibleRatio: 1 }

const layout = { paddingLeft: 42, paddingRight: 20, paddingTop: 32, paddingBottom: 24 }
const roleLabels = ['生', '旦', '净', '丑']
const metricLabels = ['表演形式', '角色活跃', '冲突强度', '关系变化', '情绪强度']

const stageCountOptions = computed(() => Object.keys(stageBuckets.value).map(Number).sort((a, b) => b - a))
const filteredScriptKeys = computed(() => {
  const key = stageCountFilter.value
  return key && stageBuckets.value[key] ? stageBuckets.value[key] : Object.keys(scripts.value)
})
const scriptOptions = computed(() =>
  pinFeaturedPlays(
    filteredScriptKeys.value.map((key) => scripts.value[key]).filter(Boolean),
    (script) => script.plainName,
  ),
)
const scriptSelectOptions = computed(() =>
  scriptOptions.value.map((script) => ({ value: script.key, label: script.name })),
)
const currentScript = computed(() => scripts.value[currentScriptKey.value] || null)
const currentStages = computed(() => currentScript.value?.stages || [])
const currentStageIndicator = computed(() => {
  if (loading.value) return '加载中...'
  if (!currentScript.value) return '暂无剧本数据'
  if (globalProgress.value === 0) return '起步 · 大幕初启'
  return `${currentState.value.stage || '-'} · ${currentState.value.theme || '-'}`
})
const panelSceneText = computed(() => {
  if (!currentScript.value) return '-'
  if (globalProgress.value === 0) return '准备推演...'
  return `场次：${currentState.value.label || '-'} ｜ 主题：${currentState.value.theme || '-'}`
})
const lockedMetricRows = computed(() => {
  if (!lockedScene.value) return []
  return metricLabels.map((label, index) => ({
    label,
    value: Math.round(lockedScene.value.data[index] || 0),
    color: streamColorsStroke[index],
  }))
})
const lockedInsight = computed(() => {
  if (!lockedScene.value) return ''
  const roleValues = lockedScene.value.roles.map((value) => Math.round(value || 0))
  const roleDominantIndex = roleValues.indexOf(Math.max(...roleValues))
  const metricValues = lockedScene.value.data.slice(0, 5).map((value) => Math.round(value || 0))
  const dominantIndex = metricValues.indexOf(Math.max(...metricValues))
  return `该处波峰中“${roleLabels[roleDominantIndex]}”行当占比最高（${roleValues[roleDominantIndex]}%），张力侧主要由“${metricLabels[dominantIndex]}”驱动；综合剧情强度为 ${Math.round(lockedScene.value.data[5])}%，基准流速 ${lockedScene.value.speed}，湍流震荡值 ${Math.round(lockedScene.value.turb)}。`
})

onMounted(async () => {
  await loadData()
  await nextTick()
  initCanvas()
  if (isLinkageTriggerSource()) syncFromLinkage()
  animate()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

watch(
  () => [linkageState.source, linkageState.selectedPlayId, linkageState.selectedSceneId, linkageState.selectedCharacterId, linkageState.selectedTrade],
  () => {
    if (isLinkageTriggerSource()) syncFromLinkage()
  },
)

watch(lockedScene, async () => {
  await nextTick()
  drawRadar()
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [dataset] = await Promise.all([loadQiyunDataset(), loadLinkageData().catch(() => null)])
    scripts.value = dataset.scripts
    stageBuckets.value = dataset.stageBuckets
    const counts = Object.keys(dataset.stageBuckets).map(Number).sort((a, b) => b - a)
    const defaultCount = counts.includes(5) ? 5 : counts[0]
    stageCountFilter.value = String(defaultCount || '')
    const keys = stageCountFilter.value ? dataset.stageBuckets[stageCountFilter.value] || [] : Object.keys(dataset.scripts)
    const featuredKey = keys.find((key) => dataset.scripts[key]?.plainName === FEATURED_PLAY_TITLES[0])
    currentScriptKey.value = featuredKey || keys[0] || ''
    if (currentScriptKey.value) switchScript(currentScriptKey.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'CSV 数据加载失败'
  } finally {
    loading.value = false
  }
}

function filterByStageCount(stageCount) {
  stageCountFilter.value = stageCount
  const firstKey = scriptOptions.value[0]?.key
  if (firstKey) switchScript(firstKey)
}

function switchScript(key) {
  if (!key || !scripts.value[key]) return
  currentScriptKey.value = key
  lockedScene.value = null
  infoOpen.value = false
  showFullScript()
}

function jumpToStage(stage) {
  const target = getStageCutoffProgress(stage)
  if (target === null) return
  jumpToProgress(target)
}

function jumpToProgress(targetProgress) {
  physics.visibleRatio = Math.max(0.01, Math.min(1, Number(targetProgress) || 0))
  setProgress(targetProgress)
}

function setProgress(value) {
  const nextValue = Math.max(0, Math.min(1, Number(value) || 0))
  globalProgress.value = nextValue
  currentState.value = getInterpolatedState(currentScript.value, nextValue)
  requestCanvasDraw()
}

function showFullScript() {
  physics.visibleRatio = 1
  setProgress(1)
}

function getStageCutoffProgress(stage) {
  const script = currentScript.value
  if (!script?.scenes?.length || !stage) return null

  const stageIndex = script.stages?.indexOf(stage) ?? -1
  let lastSceneIndex = -1

  script.scenes.forEach((scene, index) => {
    if (index === 0) return
    if (scene.stage === stage) {
      lastSceneIndex = index
      return
    }

    const sceneStageIndex = script.stages?.indexOf(scene.stage) ?? -1
    if (stageIndex >= 0 && sceneStageIndex >= 0 && sceneStageIndex <= stageIndex) {
      lastSceneIndex = index
    }
  })

  if (lastSceneIndex > 0) {
    return lastSceneIndex / Math.max(1, script.scenes.length - 1)
  }

  const fallback = script.stageProgress?.[stage]
  return Number.isFinite(fallback) ? fallback : null
}

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  resizeHandler = resizeCanvas
  window.addEventListener('resize', resizeHandler)
  resizeCanvas()
}

function resizeCanvas() {
  const canvas = canvasRef.value
  const panel = canvasPanelRef.value
  if (!canvas || !panel || !ctx) return

  const rect = panel.getBoundingClientRect()
  if (!rect.width || !rect.height) return

  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.round(rect.width * ratio)
  canvas.height = Math.round(rect.height * ratio)
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
  requestCanvasDraw()
}

function animate() {
  if (needsDraw) {
    drawChart()
    needsDraw = false
  }
  animationFrameId = requestAnimationFrame(animate)
}

function requestCanvasDraw() {
  needsDraw = true
}

function drawChart() {
  const canvas = canvasRef.value
  const panel = canvasPanelRef.value
  if (!canvas || !panel || !ctx || !currentScript.value) return

  const ratio = window.devicePixelRatio || 1
  const rect = panel.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const targetWidth = Math.round(rect.width * ratio)
  const targetHeight = Math.round(rect.height * ratio)
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) resizeCanvas()

  const w = canvas.width / ratio
  const h = canvas.height / ratio
  const graphW = Math.max(10, w - layout.paddingLeft - layout.paddingRight)
  const graphH = Math.max(10, h - layout.paddingTop - layout.paddingBottom)
  const baseY = h - layout.paddingBottom

  ctx.clearRect(0, 0, w, h)
  drawAxes(w, graphW, graphH, baseY)

  const visibleRatio = Math.max(0.01, Math.min(1, physics.visibleRatio || 1))
  const currentProgress = Math.min(globalProgress.value, visibleRatio)
  const currentTrackerX = layout.paddingLeft + (currentProgress / visibleRatio) * graphW
  trackerXCss = currentTrackerX
  activeAnchors = []

  const steps = 80
  for (let lineIndex = 0; lineIndex < 6; lineIndex++) {
    const points = []
    for (let i = 0; i <= steps; i++) {
      const displayX = i / steps
      const relativeX = displayX * visibleRatio
      const xPixel = layout.paddingLeft + displayX * graphW

      const state = getInterpolatedState(currentScript.value, relativeX)
      const val = state.data[lineIndex]
      points.push({ x: xPixel, y: Math.min(baseY, baseY - (val * graphH) / 100) })
    }

    if (points.length < 2) continue

    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    drawSmoothLine(points)
    ctx.strokeStyle = streamColorsStroke[lineIndex]
    ctx.lineWidth = lineIndex === 5 ? 2.4 : 1.9
    ctx.stroke()

    if (lineIndex === 5) drawSceneAnchors(graphW, graphH, baseY, visibleRatio)
  }

  ctx.strokeStyle = isHovering.value ? 'rgba(143, 47, 36, 0.82)' : 'rgba(95, 130, 200, 0.28)'
  ctx.lineWidth = 1
  ctx.setLineDash(isHovering.value ? [] : [4, 4])
  ctx.beginPath()
  ctx.moveTo(currentTrackerX, layout.paddingTop - 5)
  ctx.lineTo(currentTrackerX, baseY)
  ctx.stroke()
  ctx.setLineDash([])
}

function drawAxes(w, graphW, graphH, baseY) {
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  ctx.fillStyle = '#7a2e27'
  ctx.font = 'bold 10px KaiTi, STKaiti, serif'
  ctx.fillText('[ 张力强度 ]', layout.paddingLeft + 24, layout.paddingTop - 13)

  ctx.textBaseline = 'middle'
  ctx.font = '9px KaiTi, STKaiti, serif'
  ;[25, 50, 75, 100].forEach((value) => {
    const y = baseY - (value * graphH) / 100
    ctx.strokeStyle = 'rgba(95, 130, 200, 0.08)'
    ctx.beginPath()
    ctx.moveTo(layout.paddingLeft, y)
    ctx.lineTo(w - layout.paddingRight, y)
    ctx.stroke()
    ctx.fillStyle = '#9a7350'
    ctx.fillText(`${value}%`, layout.paddingLeft - 5, y)
  })

  const script = currentScript.value
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  script.axisXLabels.forEach((label, index) => {
    const ratio = (index + 1) / Math.max(1, script.axisXLabels.length)
    if (ratio <= physics.visibleRatio + 0.0001) {
      const x = layout.paddingLeft + (ratio / Math.max(0.01, physics.visibleRatio)) * graphW
      const activeWindow = 0.5 / Math.max(1, script.axisXLabels.length)
      const isActive = Math.abs(ratio - globalProgress.value) <= activeWindow
      ctx.strokeStyle = 'rgba(95, 130, 200, 0.12)'
      ctx.beginPath()
      ctx.moveTo(x, baseY)
      ctx.lineTo(x, baseY + 4)
      ctx.stroke()
      ctx.fillStyle = isActive ? '#8f2f24' : '#806a58'
      ctx.font = isActive ? 'bold 10px KaiTi, STKaiti, serif' : '9px KaiTi, STKaiti, serif'
      ctx.fillText(shortLabel(label), x, baseY + 6)
    }
  })

  ctx.strokeStyle = 'rgba(143, 47, 36, 0.2)'
  ctx.beginPath()
  ctx.moveTo(layout.paddingLeft, baseY)
  ctx.lineTo(w - layout.paddingRight, baseY)
  ctx.stroke()
}

function drawSceneAnchors(graphW, graphH, baseY, visibleRatio) {
  currentScript.value.scenes.forEach((scene, index) => {
    if (index === 0) return
    const ratio = index / Math.max(1, currentScript.value.scenes.length - 1)
    if (ratio > visibleRatio + 0.0001) return

    const x = layout.paddingLeft + (ratio / Math.max(0.01, visibleRatio)) * graphW
    const value = scene.data[5]
    const y = baseY - (value * graphH) / 100
    const isLocked = lockedScene.value?.sceneId === scene.sceneId

    activeAnchors.push({ x, y, scene })
    ctx.fillStyle = isLocked ? '#8f2f24' : streamColorsStroke[5]
    ctx.beginPath()
    ctx.arc(x, y, isLocked ? 5.8 : 4.2, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = isLocked ? '#8f2f24' : '#4A4A4A'
    ctx.font = isLocked ? 'bold 11px KaiTi, STKaiti, serif' : 'bold 10px KaiTi, STKaiti, serif'
    ctx.textAlign = 'center'
    ctx.fillText(`【${shortLabel(scene.theme, 5)}】`, x, y - 12)
  })
}

function drawSmoothLine(points) {
  for (let index = 0; index < points.length - 1; index++) {
    const cp = getBezierControlPoints(points, index, 0.25, 0.25)
    if (index === 0) ctx.quadraticCurveTo(cp.cp2x, cp.cp2y, points[index + 1].x, points[index + 1].y)
    else if (index === points.length - 2) ctx.quadraticCurveTo(cp.cp1x, cp.cp1y, points[index + 1].x, points[index + 1].y)
    else ctx.bezierCurveTo(cp.cp1x, cp.cp1y, cp.cp2x, cp.cp2y, points[index + 1].x, points[index + 1].y)
  }
}

function getBezierControlPoints(points, index, a, b) {
  const p0 = points[index - 1] || points[index]
  const p1 = points[index]
  const p2 = points[index + 1] || points[index]
  const p3 = points[index + 2] || points[index + 1] || points[index]
  const d1 = Math.hypot(p1.x - p0.x, p1.y - p0.y)
  const d2 = Math.hypot(p2.x - p1.x, p2.y - p1.y)
  const d3 = Math.hypot(p3.x - p2.x, p3.y - p2.y)
  const fa = (a * d2) / (d1 + d2) || 0
  const fb = (b * d2) / (d2 + d3) || 0
  return {
    cp1x: p1.x + fa * (p2.x - p0.x),
    cp1y: p1.y + fa * (p2.y - p0.y),
    cp2x: p2.x - fb * (p3.x - p1.x),
    cp2y: p2.y - fb * (p3.y - p1.y),
  }
}

function getInterpolatedState(script, progress) {
  if (!script?.scenes?.length) return makeEmptyState()
  const arr = script.scenes
  const safeProgress = Math.max(0, Math.min(1, progress))
  const floatIndex = safeProgress * (arr.length - 1)
  const leftIndex = Math.floor(floatIndex)
  const rightIndex = Math.min(leftIndex + 1, arr.length - 1)
  const t = floatIndex - leftIndex
  const smoothT = t * t * (3 - 2 * t)
  const left = arr[leftIndex]
  const right = arr[rightIndex]
  const nearest = arr[Math.round(floatIndex)] || left

  return {
    ...nearest,
    data: left.data.map((value, index) => value + ((right.data[index] || 0) - value) * smoothT),
    speed: left.speed + (right.speed - left.speed) * smoothT,
    turb: left.turb + (right.turb - left.turb) * smoothT,
  }
}

function handleCanvasMouseMove(event) {
  const panel = canvasPanelRef.value
  if (!panel) return
  const rect = panel.getBoundingClientRect()
  const mouseX = event.clientX - rect.left
  const previousHovering = isHovering.value
  const previousAnchor = hoveringAnchor.value
  currentMouseY = event.clientY - rect.top
  hoveringAnchor.value = activeAnchors.some((anchor) => Math.hypot(mouseX - anchor.x, currentMouseY - anchor.y) < 12)
  isHovering.value = Math.abs(mouseX - trackerXCss) < 30

  if (isHovering.value && tooltipRef.value) {
    let left = trackerXCss + 15
    if (left + 220 > rect.width) left = trackerXCss - 230
    tooltipRef.value.style.left = `${Math.max(8, left)}px`
    tooltipRef.value.style.top = `${Math.max(8, Math.min(currentMouseY - 20, rect.height - 92))}px`
  }
  if (previousHovering !== isHovering.value || previousAnchor !== hoveringAnchor.value) requestCanvasDraw()
}

function handleCanvasMouseLeave() {
  const shouldRedraw = isHovering.value || hoveringAnchor.value
  isHovering.value = false
  hoveringAnchor.value = false
  if (shouldRedraw) requestCanvasDraw()
}

function handleCanvasClick(event) {
  const panel = canvasPanelRef.value
  if (!panel) return
  const rect = panel.getBoundingClientRect()
  const mouseX = event.clientX - rect.left
  const mouseY = event.clientY - rect.top
  const anchor = activeAnchors.find((item) => Math.hypot(mouseX - item.x, mouseY - item.y) < 15)

  if (anchor) {
    lockedScene.value = anchor.scene
    analysisOpen.value = true
    infoOpen.value = false
    requestCanvasDraw()
  } else if (lockedScene.value) {
    lockedScene.value = null
    requestCanvasDraw()
  }
}

function drawRadar() {
  const canvas = radarCanvasRef.value
  if (!canvas || !lockedScene.value) return
  const radarCtx = canvas.getContext('2d')
  const w = canvas.width
  const h = canvas.height
  const cx = w / 2
  const cy = h / 2 + 4
  const r = Math.min(w, h) * 0.34
  const values = lockedScene.value.roles
  const angles = [0, Math.PI / 2, Math.PI, Math.PI * 1.5].map((angle) => angle - Math.PI / 4)

  radarCtx.clearRect(0, 0, w, h)
  radarCtx.strokeStyle = '#E6DCD3'
  radarCtx.lineWidth = 1
  for (let i = 1; i <= 4; i++) {
    radarCtx.beginPath()
    for (let j = 0; j < roleLabels.length; j++) {
      const x = cx + Math.cos(angles[j]) * ((r * i) / 4)
      const y = cy + Math.sin(angles[j]) * ((r * i) / 4)
      if (j === 0) radarCtx.moveTo(x, y)
      else radarCtx.lineTo(x, y)
    }
    radarCtx.closePath()
    radarCtx.stroke()
  }

  radarCtx.fillStyle = '#998370'
  radarCtx.font = '13px KaiTi, STKaiti, serif'
  radarCtx.textAlign = 'center'
  radarCtx.textBaseline = 'middle'
  roleLabels.forEach((label, index) => {
    radarCtx.beginPath()
    radarCtx.moveTo(cx, cy)
    radarCtx.lineTo(cx + Math.cos(angles[index]) * r, cy + Math.sin(angles[index]) * r)
    radarCtx.stroke()
    radarCtx.fillText(`${label} (${['Sheng', 'Dan', 'Jing', 'Chou'][index]})`, cx + Math.cos(angles[index]) * (r + 28), cy + Math.sin(angles[index]) * (r + 24))
  })

  radarCtx.beginPath()
  values.forEach((value, index) => {
    const x = cx + Math.cos(angles[index]) * (r * (value / 100))
    const y = cy + Math.sin(angles[index]) * (r * (value / 100))
    if (index === 0) radarCtx.moveTo(x, y)
    else radarCtx.lineTo(x, y)
  })
  radarCtx.closePath()
  radarCtx.fillStyle = 'rgba(179, 92, 55, 0.3)'
  radarCtx.fill()
  radarCtx.strokeStyle = '#B35C37'
  radarCtx.lineWidth = 2
  radarCtx.stroke()

  radarCtx.fillStyle = '#B35C37'
  values.forEach((value, index) => {
    radarCtx.beginPath()
    radarCtx.arc(cx + Math.cos(angles[index]) * (r * (value / 100)), cy + Math.sin(angles[index]) * (r * (value / 100)), 3, 0, Math.PI * 2)
    radarCtx.fill()
  })
}

function syncFromLinkage() {
  if (!Object.keys(scripts.value).length || !linkageState.selectedPlayId) return
  const play = linkageState.plays.find((item) => item.play_id === linkageState.selectedPlayId)
  const key = findScriptKeyByPlay(scripts.value, linkageState.selectedPlayId, play?.title)
  if (!key) return
  if (currentScriptKey.value !== key) switchScript(key)

  const sceneNo =
    sceneNoFromSceneId(linkageState.selectedSceneId) ||
    sceneNoFromSceneId(play?.characters?.find((item) => item.character_id === linkageState.selectedCharacterId)?.primary_scene_id)
  if (sceneNo) jumpToSceneNo(sceneNo)
}

function jumpToSceneNo(sceneNo) {
  const script = currentScript.value
  if (!script) return
  const index = script.scenes.findIndex((scene) => scene.sceneNo === sceneNo)
  if (index > 0) jumpToProgress(index / Math.max(1, script.scenes.length - 1), true)
}

function isLinkageTriggerSource() {
  return linkageState.source === 'leftTopIcon' || linkageState.source === 'rightTopNode'
}

function shortLabel(label, max = 4) {
  const value = String(label || '')
  return value.length > max ? `${value.slice(0, max)}…` : value
}

function compactLegendName(name, index) {
  return ['表演', '角色', '冲突', '关系', '情绪', '综合'][index] || name
}

function makeEmptyState() {
  return {
    data: [0, 0, 0, 0, 0, 0],
    speed: 0.02,
    turb: 5,
    stage: '加载中',
    theme: '',
    label: '-',
    desc: '暂无数据',
    roles: [25, 25, 25, 25],
  }
}
</script>

<style scoped>
.qiyun-view {
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #4a3b32;
  background: #FBF6E9;
  font-family: "STKaiti", "KaiTi", serif;
}

.qiyun-card {
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 4px 5px 5px;
  overflow: hidden;
  background: #FBF6E9;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.qiyun-topbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  min-height: 26px;
  margin-bottom: 3px;
  flex: 0 0 auto;
  overflow: hidden;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: 0 1 330px;
}

.select-box {
  display: flex;
  align-items: center;
  height: 24px;
  min-width: 0;
  padding: 0 6px;
  background: rgba(251, 246, 233, 0.72);
  border: 1px solid rgba(143, 47, 36, 0.26);
  border-radius: 4px;
  box-shadow: none;
}

.stage-count-box {
  flex: 0 0 122px;
}

.script-box {
  flex: 1 1 170px;
}

.select-box select {
  width: 100%;
  min-width: 0;
  color: #7a2e27;
  font: 800 12px/1.2 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 0;
  outline: 0;
  cursor: pointer;
}

.script-box .play-select {
  width: 100%;
  height: 100%;
  color: #8f2f24;
  font: 800 12px/1.2 "STKaiti", "KaiTi", serif;
}

.stage-container {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 2px;
  min-width: 0;
  flex: 0 0 auto;
  max-width: none;
  padding: 0;
  overflow-x: auto;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.stage-btn {
  height: 22px;
  min-width: 34px;
  padding: 0 6px;
  white-space: nowrap;
  color: #8f2f24;
  font-size: 11px;
  font-weight: 800;
  background: rgba(251, 246, 233, 0.44);
  border: 1px solid rgba(143, 47, 36, 0.26);
  border-radius: 999px;
  cursor: pointer;
}

.stage-btn.active {
  color: #fff;
  background: #8f2f24;
  border-color: #8f2f24;
}

.qiyun-legend {
  display: flex;
  align-items: center;
  gap: 5px;
  min-height: 24px;
  margin-bottom: 0;
  padding: 0;
  overflow: hidden;
  font: 11px/1.2 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  flex: 1 1 270px;
}

.legend-title {
  flex: 0 0 auto;
  color: #806a58;
  font-weight: 800;
}

.legend-list {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px 7px;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  color: #4b3328;
  font-weight: 700;
}

.legend-item i {
  width: 8px;
  height: 8px;
  margin-right: 3px;
  border-radius: 50%;
}

.qiyun-main {
  position: relative;
  display: block;
  flex: 1 1 auto;
  min-height: 0;
}

.canvas-panel,
.analysis-panel {
  position: relative;
  min-height: 0;
  overflow: hidden;
  background: #FBF6E9;
  border: 0;
  border-radius: 0;
}

.canvas-panel {
  width: 100%;
  height: 100%;
  box-shadow: none;
}

.canvas-heading {
  position: absolute;
  top: 8px;
  left: 84px;
  right: 54px;
  z-index: 2;
  pointer-events: none;
}

.canvas-heading span {
  display: block;
  overflow: hidden;
  color: #8f2f24;
  font-size: 14px;
  font-weight: 900;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.analytical-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  cursor: default;
}

.analytical-canvas.clickable {
  cursor: pointer;
}

.cursor-tooltip {
  position: absolute;
  z-index: 5;
  width: 190px;
  padding: 7px 8px;
  pointer-events: none;
  opacity: 0;
  background: rgba(251, 246, 233, 0.95);
  border: 1px solid rgba(143, 47, 36, 0.16);
  border-radius: 6px;
  box-shadow: none;
  transition: opacity 0.15s ease-out;
}

.cursor-tooltip.visible {
  opacity: 1;
}

.tooltip-title {
  padding-bottom: 4px;
  margin-bottom: 5px;
  color: #4a3b32;
  font-size: 11px;
  font-weight: 800;
  border-bottom: 1px solid rgba(143, 47, 36, 0.13);
}

.tooltip-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 7px;
  font: 10px/1.2 "STKaiti", "KaiTi", serif;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 4px;
}

.analysis-panel {
  position: absolute;
  top: 8px;
  right: 16px;
  bottom: 8px;
  left: 16px;
  z-index: 9;
  display: flex;
  flex-direction: column;
  padding: 8px 10px;
  overflow: hidden;
  pointer-events: none;
  opacity: 0;
  background: rgba(251, 246, 233, 0.96);
  border: 1px solid rgba(143, 47, 36, 0.18);
  border-radius: 6px;
  transform: translateY(8px);
  box-shadow: none;
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.analysis-panel.open {
  pointer-events: auto;
  opacity: 1;
  transform: translateY(0);
  box-shadow: none;
}

.analysis-backdrop {
  position: absolute;
  inset: 0;
  z-index: 8;
  background: transparent;
  backdrop-filter: none;
}

.analysis-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  height: 22px;
  padding: 0 8px;
  color: #8f2f24;
  font: 900 12px/1 "STKaiti", "KaiTi", serif;
  white-space: nowrap;
  background: transparent;
  border: 1px solid rgba(143, 47, 36, 0.32);
  border-radius: 999px;
  box-shadow: none;
  cursor: pointer;
}

.analysis-toggle::before {
  width: 5px;
  height: 5px;
  margin-right: 4px;
  content: "";
  background: #8f2f24;
  border-radius: 50%;
  box-shadow: none;
}

.analysis-toggle.active {
  color: #fff;
  background: #8f2f24;
  border-color: #8f2f24;
}

.analysis-toggle.active::before {
  background: #fff8ed;
  box-shadow: none;
}

.panel-title-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.14);
}

.panel-title-row > strong {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: #8f2f24;
  font-size: 14px;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-btn {
  display: inline-grid;
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  place-items: center;
  color: #806a58;
  font: 800 11px/1 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 1px solid rgba(143, 47, 36, 0.22);
  border-radius: 50%;
  cursor: pointer;
}

.panel-close-btn {
  flex: 0 0 auto;
  height: 18px;
  padding: 0 6px;
  color: #806a58;
  font: 800 10px/1 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 0;
  border-radius: 0;
  cursor: pointer;
}

.info-tooltip {
  position: absolute;
  top: 24px;
  left: 0;
  z-index: 8;
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: min(280px, 90vw);
  padding: 9px;
  color: #5c4636;
  font: 11px/1.45 "STKaiti", "KaiTi", serif;
  pointer-events: none;
  opacity: 0;
  background: rgba(251, 246, 233, 0.97);
  border: 1px solid rgba(143, 47, 36, 0.2);
  border-radius: 6px;
  box-shadow: none;
  transition: opacity 0.18s ease;
}

.info-tooltip.visible {
  pointer-events: auto;
  opacity: 1;
}

.info-tooltip b {
  color: #8f2f24;
}

.scene-loc-box {
  display: flex;
  align-items: baseline;
  gap: 2px;
  min-width: 0;
  padding: 0 0 4px;
  margin-bottom: 5px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.12);
}

.scene-loc-box span {
  display: inline;
  flex: 0 0 auto;
  margin-bottom: 0;
  color: #8f2f24;
  font: 900 12px/1.2 "STKaiti", "KaiTi", serif;
}

.scene-loc-box b {
  display: block;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  color: #4a3b32;
  font: 800 12px/1.45 "STKaiti", "KaiTi", serif;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desc-block {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  padding-right: 3px;
}

.desc-title {
  display: block;
  flex: 0 0 auto;
  margin-bottom: 5px;
  color: #8f2f24;
  font-size: 13px;
  font-weight: 900;
}

.normal-desc,
.locked-insight {
  flex: 1 1 auto;
  min-height: 0;
  padding-right: 3px;
  margin: 0;
  overflow-y: auto;
  color: #5c4636;
  font: 12px/1.7 "STKaiti", "KaiTi", serif;
  text-align: justify;
}

.normal-desc small {
  display: inline;
  padding-bottom: 0;
  margin: 0 6px 0 0;
  color: #806a58;
  border-bottom: 0;
}

.locked-inline-summary {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 3px 12px;
  flex: 0 0 auto;
  margin-bottom: 5px;
}

.locked-inline-summary span {
  display: inline-flex;
  align-items: baseline;
  gap: 1px;
  min-width: 0;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.locked-inline-summary small {
  display: inline;
  margin-bottom: 0;
  overflow: hidden;
  color: #806a58;
  font: 800 11px/1.25 "STKaiti", "KaiTi", serif;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.locked-inline-summary small::after {
  content: "：";
}

.locked-inline-summary b {
  display: inline;
  max-width: 96px;
  overflow: hidden;
  color: #4a3b32;
  font: 900 12px/1.25 "STKaiti", "KaiTi", serif;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-card {
  flex: 0 0 auto;
  padding: 4px 0;
  margin-bottom: 6px;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-row {
  padding: 2px 0;
  color: #5c4636;
  font: 11px/1.2 "STKaiti", "KaiTi", serif;
  border-bottom: 1px solid rgba(143, 47, 36, 0.08);
}

.metric-row i {
  flex: 1 1 auto;
  height: 5px;
  overflow: hidden;
  background: rgba(95, 130, 200, 0.15);
  border-radius: 999px;
}

.metric-row em {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.metric-row b {
  flex: 0 0 34px;
  text-align: right;
}

.metric-cells {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px;
  margin-top: 5px;
}

.metric-cells span {
  display: grid;
  gap: 2px;
  place-items: center;
  padding: 2px 0;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.metric-cells small {
  color: #806a58;
  font-size: 10px;
}

.metric-cells b {
  color: #8f2f24;
  font-size: 11px;
}

.locked-insight {
  flex: 1 1 auto;
  max-height: 50px;
  padding: 4px 0 0;
  overflow-y: auto;
  background: transparent;
  border: 0;
  border-radius: 0;
  font-size: 11px;
  line-height: 1.45;
}

.locked-insight b {
  color: #8f2f24;
}

.hover-hint {
  flex: 0 0 auto;
  padding: 3px 0 0;
  margin-top: 5px;
  color: #8f2f24;
  font: 800 11px/1.2 "STKaiti", "KaiTi", serif;
  text-align: center;
  background: transparent;
  border: 0;
  border-radius: 0;
}

.load-state {
  position: absolute;
  inset: 40px 12px 12px;
  z-index: 10;
  display: grid;
  place-items: center;
  color: #7a2e27;
  font-size: 13px;
  font-weight: 800;
  text-align: center;
  background: rgba(251, 246, 233, 0.9);
}

.load-state.error {
  color: #8f2f24;
}

@media (max-width: 900px) {
  .stage-container {
    flex: 1 1 auto;
  }

  .selector-group {
    flex-basis: 250px;
  }
}
</style>
