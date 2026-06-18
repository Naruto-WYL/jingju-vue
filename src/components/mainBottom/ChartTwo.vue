<template>
  <section class="compare-view">
    <div class="compare-card">
      <div class="compare-legend">
        <span class="legend-title">五类叙事结构曲线对比：</span>
        <button
          v-for="key in activeCompareKeys"
          :key="key"
          type="button"
          class="legend-item"
          :class="{ muted: hasFocusedKeys && !focusedKeySet.has(key), active: focusedKeySet.has(key) }"
          :style="{ color: colorForKey(key) }"
          @mouseenter="hoveredCompareKey = key"
          @mouseleave="hoveredCompareKey = ''"
          @click="toggleCompareKey(key)"
        >
          <i :style="{ background: colorForKey(key) }"></i>{{ compareScripts[key]?.name }}
        </button>
      </div>

      <div class="compare-main">
        <div ref="canvasPanelRef" class="compare-canvas-panel">
          <div class="canvas-heading">
            <span>五类宏观叙事结构曲线叠加</span>
          </div>
          <canvas ref="canvasRef" class="compare-canvas"></canvas>
        </div>

        <aside class="compare-panel">
          <div class="panel-title-row">
            <strong>五类叙事结构特征归纳</strong>
          </div>
          <div class="desc-block">
            <span class="desc-title">{{ focusTitle }}</span>
            <div class="compare-desc-list">
              <article
                v-for="key in panelKeys"
                :key="key"
                class="compare-desc-card"
                :class="{ focused: focusedKeySet.has(key) }"
              >
                <h4 :style="{ color: colorForKey(key) }">
                  ■ {{ compareScripts[key]?.mode }}
                  <small>（{{ compareScripts[key]?.sampleCount || 0 }}本）</small>
                </h4>
                <p><b>【高阶学术定义】</b>{{ compareScripts[key]?.definition }}</p>
                <p><b>【量化划分规则】</b>{{ compareScripts[key]?.rule }}</p>
                <p><b>【原型线数据】</b>{{ curveText(compareScripts[key]) }}</p>
                <em>代表剧本：{{ representativeText(compareScripts[key]) }}</em>
              </article>
            </div>
          </div>
        </aside>
      </div>

      <div v-if="loading || errorMessage" class="load-state" :class="{ error: errorMessage }">
        {{ errorMessage || '叙事模式数据加载中...' }}
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  classifyFiveStageCurve,
  compareColorsStroke,
  compareKeys,
  findScriptKeyByPlay,
  getFiveStageValues,
  loadQiyunDataset,
} from './qiyunData'
import { linkageState, loadLinkageData } from '../../services/linkageStore'
import { loopFilterState } from '../../services/loopFilterStore'
import { loadDemoDataset } from '../services/tableImport'

const canvasPanelRef = ref(null)
const canvasRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const scripts = ref({})
const compareScripts = ref({})
const loopFlows = ref([])
const hoveredCompareKey = ref('')
const selectedCompareKey = ref('')

let ctx = null
let animationFrameId = 0
let resizeHandler = null
const layout = { paddingLeft: 42, paddingRight: 24, paddingTop: 34, paddingBottom: 27 }

const activeCompareKeys = computed(() => compareKeys.filter((key) => compareScripts.value[key]))
const linkedCompareKeys = computed(() => {
  const scope = loopFilterState.scope
  const flow = loopFilterState.flow
  if (!scope) return []

  const scopedKeys = compareKeys.filter((key) =>
    (Array.isArray(scope.narrativeTypes) ? scope.narrativeTypes : []).some(
      (narrativeType) => narrativeTypeKey(narrativeType) === key,
    ),
  )
  if (scopedKeys.length) return scopedKeys

  const matchedFlows = loopFlows.value.filter((item) => {
    if (scope.type === 'relation') return item.relationType === scope.relationType
    if (scope.type === 'theme') {
      return item.relationType === scope.relationType && item.themeCombo === scope.themeCombo
    }
    if (scope.type === 'flow') return item.id === scope.flowId
    return flow?.id ? item.id === flow.id : false
  })

  const typeWeights = new Map()
  matchedFlows.forEach((item) => {
    const key = narrativeTypeKey(item.narrativeType)
    if (!key || !activeCompareKeys.value.includes(key)) return
    typeWeights.set(key, (typeWeights.get(key) || 0) + Math.max(1, Number(item.count) || 0))
  })

  const limit = scope.type === 'flow' ? 1 : 3
  return Array.from(typeWeights.entries())
    .sort((a, b) => b[1] - a[1] || compareKeys.indexOf(a[0]) - compareKeys.indexOf(b[0]))
    .slice(0, limit)
    .map(([key]) => key)
})
const focusedKeys = computed(() => {
  if (hoveredCompareKey.value) return [hoveredCompareKey.value]
  if (selectedCompareKey.value) return [selectedCompareKey.value]
  return linkedCompareKeys.value
})
const focusedKeySet = computed(() => new Set(focusedKeys.value))
const hasFocusedKeys = computed(() => focusedKeys.value.length > 0)
const panelKeys = computed(() => (hasFocusedKeys.value ? focusedKeys.value : activeCompareKeys.value))
const focusTitle = computed(() => {
  if (!hasFocusedKeys.value) return '宏观结构提炼：'
  if (focusedKeys.value.length === 1) return `${compareScripts.value[focusedKeys.value[0]]?.mode || '结构类型'}：`
  return `中上联动结构（${focusedKeys.value.length}类）：`
})
const loopScopeSignature = computed(() => {
  const scope = loopFilterState.scope
  if (!scope) return ''
  const narrativeTypes = Array.isArray(scope.narrativeTypes) ? scope.narrativeTypes.join('|') : ''
  if (scope.type === 'relation') return `relation:${scope.relationType}:${narrativeTypes}`
  if (scope.type === 'theme') return `theme:${scope.relationType}:${scope.themeCombo}:${narrativeTypes}`
  return `flow:${scope.flowId || loopFilterState.flow?.id || ''}:${narrativeTypes}`
})

onMounted(async () => {
  await loadData()
  await nextTick()
  initCanvas()
  if (!loopFilterState.scope && isLinkageTriggerSource()) syncFromLinkage()
  animate()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

watch(
  () => [linkageState.source, linkageState.selectedPlayId],
  () => {
    if (!loopFilterState.scope && isLinkageTriggerSource()) syncFromLinkage()
  },
)

watch([hoveredCompareKey, selectedCompareKey, linkedCompareKeys], () => {
  drawCompare()
})

watch(loopScopeSignature, () => {
  selectedCompareKey.value = ''
  hoveredCompareKey.value = ''
  drawCompare()
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [dataset, , loopDataset] = await Promise.all([
      loadQiyunDataset(),
      loadLinkageData().catch(() => null),
      loadDemoDataset().catch(() => ({ flows: [] })),
    ])
    scripts.value = dataset.scripts
    compareScripts.value = dataset.compareScripts
    loopFlows.value = loopDataset.flows || []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '叙事模式数据加载失败'
  } finally {
    loading.value = false
  }
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
}

function animate() {
  drawCompare()
  animationFrameId = requestAnimationFrame(animate)
}

function drawCompare() {
  const canvas = canvasRef.value
  const panel = canvasPanelRef.value
  if (!canvas || !panel || !ctx || !activeCompareKeys.value.length) return

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

  const drawKeys = hasFocusedKeys.value
    ? activeCompareKeys.value.filter((key) => !focusedKeySet.value.has(key)).concat(focusedKeys.value)
    : activeCompareKeys.value

  drawKeys.forEach((key) => {
    const script = compareScripts.value[key]
    if (!script?.scenes?.length) return
    const color = colorForKey(key)
    const isFocused = focusedKeySet.value.has(key)
    const isFaded = hasFocusedKeys.value && !isFocused
    const smoothPoints = []
    const steps = 80

    for (let i = 0; i <= steps; i++) {
      const t = i / steps
      const x = layout.paddingLeft + t * graphW
      const value = getCompareValue(script, t)
      smoothPoints.push({ x, y: baseY - (value * graphH) / 100 })
    }

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(smoothPoints[0].x, smoothPoints[0].y)
    drawSmoothLine(smoothPoints)
    ctx.strokeStyle = color
    ctx.globalAlpha = isFaded ? 0.18 : 0.96
    ctx.lineWidth = isFocused ? 2.7 : 2.1
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.stroke()
    ctx.restore()

    if (isFocused) drawPeakAnchor(script, smoothPoints, color, w, h, focusedKeys.value.length === 1)
  })
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
    ctx.fillStyle = '#806a58'
    ctx.fillText(`${value}%`, layout.paddingLeft - 5, y)
  })

  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  ;['开端', '发展', '转折', '高潮', '结局'].forEach((label, index) => {
    const x = layout.paddingLeft + (index / 4) * graphW
    ctx.strokeStyle = 'rgba(95, 130, 200, 0.14)'
    ctx.beginPath()
    ctx.moveTo(x, baseY)
    ctx.lineTo(x, baseY + 4)
    ctx.stroke()
    ctx.fillStyle = '#806a58'
    ctx.font = '10px KaiTi, STKaiti, serif'
    ctx.fillText(label, x, baseY + 6)
  })

  ctx.strokeStyle = 'rgba(143, 47, 36, 0.22)'
  ctx.beginPath()
  ctx.moveTo(layout.paddingLeft, baseY)
  ctx.lineTo(w - layout.paddingRight, baseY)
  ctx.stroke()
}

function drawPeakAnchor(script, points, color, w, h, showLabel = true) {
  let peakIndex = 0
  let minY = h
  let maxY = 0
  points.forEach((point, index) => {
    if (point.y < minY) {
      minY = point.y
      peakIndex = index
    }
    if (point.y > maxY) maxY = point.y
  })
  if (maxY - minY < 5) peakIndex = Math.floor(points.length / 2)
  else if (peakIndex < 5) peakIndex = 5
  else if (peakIndex > points.length - 5) peakIndex = points.length - 5

  const point = points[peakIndex]
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(point.x, point.y, 4.2, 0, Math.PI * 2)
  ctx.fill()

  if (!showLabel) return

  const labelText = `【${script.name.replace(/[《》]/g, '')}】`
  const plotWidth = Math.max(1, w - layout.paddingLeft - layout.paddingRight)
  const horizontalRatio = (point.x - layout.paddingLeft) / plotWidth
  let align = 'center'
  let textX = point.x
  if (horizontalRatio < 0.38) {
    align = 'left'
    textX = point.x + 14
  } else if (horizontalRatio > 0.62) {
    align = 'right'
    textX = point.x - 14
  }

  const placeAbove = point.y > layout.paddingTop + 30
  const textY = placeAbove ? point.y - 20 : point.y + 20

  ctx.save()
  ctx.font = 'bold 12px KaiTi, STKaiti, serif'
  ctx.textAlign = align
  ctx.textBaseline = placeAbove ? 'bottom' : 'top'

  const measuredWidth = ctx.measureText(labelText).width
  if (align === 'left') textX = Math.min(textX, w - layout.paddingRight - measuredWidth)
  if (align === 'right') textX = Math.max(textX, layout.paddingLeft + measuredWidth)
  if (align === 'center') {
    textX = Math.max(layout.paddingLeft + measuredWidth / 2, Math.min(textX, w - layout.paddingRight - measuredWidth / 2))
  }

  ctx.beginPath()
  ctx.moveTo(point.x, point.y + (placeAbove ? -6 : 6))
  ctx.lineTo(point.x, point.y + (placeAbove ? -13 : 13))
  ctx.strokeStyle = color
  ctx.globalAlpha = 0.55
  ctx.lineWidth = 1
  ctx.stroke()

  ctx.globalAlpha = 1
  ctx.lineWidth = 4
  ctx.lineJoin = 'round'
  ctx.strokeStyle = '#FBF6E9'
  ctx.strokeText(labelText, textX, textY)
  ctx.fillStyle = color
  ctx.fillText(labelText, textX, textY)
  ctx.restore()
}

function getCompareValue(script, progress) {
  const scenes = script.scenes.slice(1)
  if (!scenes.length) return 0
  const floatIndex = progress * (scenes.length - 1)
  const leftIndex = Math.floor(floatIndex)
  const rightIndex = Math.min(leftIndex + 1, scenes.length - 1)
  const localT = floatIndex - leftIndex
  const smoothT = localT * localT * (3 - 2 * localT)
  return scenes[leftIndex].data[5] + (scenes[rightIndex].data[5] - scenes[leftIndex].data[5]) * smoothT
}

function drawSmoothLine(points) {
  for (let index = 0; index < points.length - 1; index++) {
    const cp = getBezierControlPoints(points, index, 0.2, 0.2)
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

function colorForKey(key) {
  const index = Math.max(0, compareKeys.indexOf(key))
  return compareColorsStroke[index]
}

function narrativeTypeKey(value) {
  const name = String(value || '').trim()
  if (name === '平稳型') return 'flat'
  if (name === '前锋型' || name === '前峰型') return 'frontPeak'
  if (name === '后峰型') return 'backPeak'
  if (name === '中峰型') return 'midPeak'
  if (name === '多峰型') return 'multiPeak'
  return ''
}

function toggleCompareKey(key) {
  selectedCompareKey.value = selectedCompareKey.value === key ? '' : key
}

function curveText(script) {
  if (!script) return ''
  return script.scenes
    .slice(1)
    .map((scene, index) => `${script.stages[index]}${scene.data[5]}%`)
    .join(' / ')
}

function representativeText(script) {
  return script?.reps?.length ? script.reps.join('、') : '当前样本不足，暂无代表剧本'
}

function syncFromLinkage() {
  if (!Object.keys(scripts.value).length || !linkageState.selectedPlayId) return
  const play = linkageState.plays.find((item) => item.play_id === linkageState.selectedPlayId)
  const key = findScriptKeyByPlay(scripts.value, linkageState.selectedPlayId, play?.title)
  const values = getFiveStageValues(scripts.value[key])
  const typeKey = classifyFiveStageCurve(values)
  if (typeKey && compareScripts.value[typeKey]) selectedCompareKey.value = typeKey
}

function isLinkageTriggerSource() {
  return linkageState.source === 'leftTopIcon' || linkageState.source === 'rightTopNode'
}
</script>

<style scoped>
.compare-view {
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #4a3b32;
  background: #FBF6E9;
  font-family: "STKaiti", "KaiTi", serif;
}

.compare-card {
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

.compare-legend {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  min-height: 26px;
  margin-bottom: 3px;
  padding: 0;
  overflow: hidden;
  font: 12px/1.2 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.legend-title {
  flex: 0 0 auto;
  color: #806a58;
  font-weight: 800;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  padding: 0 6px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  background: rgba(251, 246, 233, 0.42);
  border: 1px solid rgba(143, 47, 36, 0.18);
  border-radius: 999px;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.legend-item i {
  width: 10px;
  height: 6px;
  border-radius: 999px;
}

.legend-item.muted {
  opacity: 0.3;
}

.legend-item.active {
  transform: translateY(-1px);
}

.compare-main {
  display: grid;
  grid-template-columns: minmax(0, 2.8fr) minmax(170px, 1fr);
  gap: 6px;
  flex: 1 1 auto;
  min-height: 0;
}

.compare-canvas-panel,
.compare-panel {
  position: relative;
  min-height: 0;
  overflow: hidden;
  background: #FBF6E9;
  border: 0;
  border-radius: 0;
}

.compare-canvas-panel {
  box-shadow: none;
}

.canvas-heading {
  position: absolute;
  top: 8px;
  left: 76px;
  right: 12px;
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

.compare-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.compare-panel {
  display: flex;
  flex-direction: column;
  padding: 6px 0 0 4px;
  box-shadow: none;
}

.panel-title-row {
  padding-bottom: 4px;
  margin-bottom: 4px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.12);
}

.panel-title-row strong {
  display: block;
  overflow: hidden;
  color: #8f2f24;
  font-size: 14px;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desc-block {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
}

.desc-title {
  display: block;
  flex: 0 0 auto;
  margin-bottom: 5px;
  color: #8f2f24;
  font-size: 13px;
  font-weight: 900;
}

.compare-desc-list {
  flex: 1 1 auto;
  min-height: 0;
  padding-right: 3px;
  overflow-y: auto;
  scrollbar-color: rgba(143, 47, 36, 0.36) #FBF6E9;
  scrollbar-width: thin;
}

.compare-desc-list::-webkit-scrollbar {
  width: 7px;
}

.compare-desc-list::-webkit-scrollbar-track {
  background: #FBF6E9;
}

.compare-desc-list::-webkit-scrollbar-thumb {
  background: rgba(143, 47, 36, 0.34);
  border: 2px solid #FBF6E9;
  border-radius: 999px;
}

.compare-desc-card {
  padding: 0 0 6px;
  margin-bottom: 7px;
  color: #5c4636;
  font: 11px/1.5 "STKaiti", "KaiTi", serif;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(143, 47, 36, 0.08);
  border-radius: 0;
  box-shadow: none;
}

.compare-desc-card.focused {
  padding: 0 0 6px;
  font-size: 12px;
}

.compare-desc-card h4 {
  margin: 0 0 5px;
  font-size: 13px;
  line-height: 1.2;
}

.compare-desc-card h4 small {
  color: #806a58;
  font-size: 10px;
  font-weight: 400;
}

.compare-desc-card p {
  margin: 0 0 4px;
  text-align: justify;
}

.compare-desc-card em {
  display: block;
  margin-top: 4px;
  color: #806a58;
  font-style: italic;
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
  .compare-main {
    grid-template-columns: minmax(0, 1fr);
  }

  .compare-panel {
    display: none;
  }
}
</style>
