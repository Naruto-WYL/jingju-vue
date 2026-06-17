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
          :class="{ muted: focusKey && focusKey !== key, active: selectedCompareKey === key || hoveredCompareKey === key }"
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
            <span class="desc-title">{{ focusKey ? `${compareScripts[focusKey]?.mode || '结构类型'}：` : '宏观结构提炼：' }}</span>
            <div class="compare-desc-list">
              <article
                v-for="key in panelKeys"
                :key="key"
                class="compare-desc-card"
                :class="{ focused: focusKey === key }"
                :style="{ borderColor: focusKey === key ? colorForKey(key) : '#E6DCD3' }"
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

const canvasPanelRef = ref(null)
const canvasRef = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const scripts = ref({})
const compareScripts = ref({})
const hoveredCompareKey = ref('')
const selectedCompareKey = ref('')

let ctx = null
let animationFrameId = 0
let resizeHandler = null
const layout = { paddingLeft: 42, paddingRight: 24, paddingTop: 34, paddingBottom: 27 }

const activeCompareKeys = computed(() => compareKeys.filter((key) => compareScripts.value[key]))
const focusKey = computed(() => hoveredCompareKey.value || selectedCompareKey.value)
const panelKeys = computed(() => (focusKey.value && activeCompareKeys.value.includes(focusKey.value) ? [focusKey.value] : activeCompareKeys.value))

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
  () => [linkageState.source, linkageState.selectedPlayId],
  () => {
    if (isLinkageTriggerSource()) syncFromLinkage()
  },
)

watch([hoveredCompareKey, selectedCompareKey], () => {
  drawCompare()
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [dataset] = await Promise.all([loadQiyunDataset(), loadLinkageData().catch(() => null)])
    scripts.value = dataset.scripts
    compareScripts.value = dataset.compareScripts
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
  canvas.width = rect.width * ratio
  canvas.height = rect.height * ratio
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
  if (canvas.width !== rect.width * ratio || canvas.height !== rect.height * ratio) resizeCanvas()

  const w = canvas.width / ratio
  const h = canvas.height / ratio
  const graphW = Math.max(10, w - layout.paddingLeft - layout.paddingRight)
  const graphH = Math.max(10, h - layout.paddingTop - layout.paddingBottom)
  const baseY = h - layout.paddingBottom

  ctx.clearRect(0, 0, w, h)
  drawAxes(w, graphW, graphH, baseY)

  const drawKeys = focusKey.value
    ? activeCompareKeys.value.filter((key) => key !== focusKey.value).concat(focusKey.value)
    : activeCompareKeys.value

  drawKeys.forEach((key) => {
    const script = compareScripts.value[key]
    if (!script?.scenes?.length) return
    const color = colorForKey(key)
    const isFaded = focusKey.value && focusKey.value !== key
    const smoothPoints = []
    const steps = 80

    for (let i = 0; i <= steps; i++) {
      const t = i / steps
      const x = layout.paddingLeft + t * graphW
      const value = getCompareValue(script, t)
      smoothPoints.push({ x, y: baseY - (value * graphH) / 100 })
    }

    ctx.beginPath()
    ctx.moveTo(smoothPoints[0].x, smoothPoints[0].y)
    drawSmoothLine(smoothPoints)
    ctx.strokeStyle = isFaded ? 'rgba(150, 150, 150, 0.15)' : color
    ctx.lineWidth = isFaded ? 1.5 : 3.4
    ctx.shadowColor = color
    ctx.shadowBlur = focusKey.value === key ? 12 : 3
    ctx.stroke()
    ctx.shadowBlur = 0

    if (focusKey.value === key) drawPeakAnchor(script, smoothPoints, color, w, h)
  })
}

function drawAxes(w, graphW, graphH, baseY) {
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  ctx.fillStyle = '#A0522D'
  ctx.font = 'bold 10px sans-serif'
  ctx.fillText('[ 张力强度 ]', layout.paddingLeft + 24, layout.paddingTop - 13)

  ctx.textBaseline = 'middle'
  ctx.font = '9px sans-serif'
  ;[25, 50, 75, 100].forEach((value) => {
    const y = baseY - (value * graphH) / 100
    ctx.strokeStyle = 'rgba(160, 82, 45, 0.06)'
    ctx.beginPath()
    ctx.moveTo(layout.paddingLeft, y)
    ctx.lineTo(w - layout.paddingRight, y)
    ctx.stroke()
    ctx.fillStyle = '#A69482'
    ctx.fillText(`${value}%`, layout.paddingLeft - 5, y)
  })

  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  ;['开端', '发展', '转折', '高潮', '结局'].forEach((label, index) => {
    const x = layout.paddingLeft + (index / 4) * graphW
    ctx.strokeStyle = 'rgba(28, 28, 28, 0.15)'
    ctx.beginPath()
    ctx.moveTo(x, baseY)
    ctx.lineTo(x, baseY + 4)
    ctx.stroke()
    ctx.fillStyle = '#998370'
    ctx.font = '10px sans-serif'
    ctx.fillText(label, x, baseY + 6)
  })

  ctx.strokeStyle = '#D9CEBF'
  ctx.beginPath()
  ctx.moveTo(layout.paddingLeft, baseY)
  ctx.lineTo(w - layout.paddingRight, baseY)
  ctx.stroke()
}

function drawPeakAnchor(script, points, color, w, h) {
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
  ctx.arc(point.x, point.y, 4, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#fff'
  ctx.beginPath()
  ctx.arc(point.x, point.y, 2, 0, Math.PI * 2)
  ctx.fill()

  let align = 'center'
  let textX = point.x
  if (point.x < layout.paddingLeft + 30) {
    align = 'left'
    textX = point.x + 8
  } else if (point.x > w - layout.paddingRight - 30) {
    align = 'right'
    textX = point.x - 8
  }

  let textY = point.y - 12
  if (point.y < layout.paddingTop + 15) textY = point.y + 20
  ctx.fillStyle = color
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = align
  ctx.fillText(`【${script.name.replace(/[《》]/g, '')}】`, textX, textY)
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
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.compare-card {
  position: relative;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 6px;
  overflow: hidden;
  background: #FBF6E9;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  box-shadow: 0 5px 14px rgba(94, 63, 42, 0.08);
}

.compare-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  min-height: 33px;
  margin-bottom: 6px;
  padding: 6px 9px;
  overflow: hidden;
  font: 12px/1.2 "Microsoft YaHei", sans-serif;
  background: #fdfbf7;
  border: 1px solid #e6dcd3;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(90, 60, 35, 0.06);
}

.legend-title {
  flex: 0 0 auto;
  color: #998370;
  font-weight: 800;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  background: transparent;
  border: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.legend-item i {
  width: 12px;
  height: 6px;
  border-radius: 2px;
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
  gap: 8px;
  flex: 1 1 auto;
  min-height: 0;
}

.compare-canvas-panel,
.compare-panel {
  position: relative;
  min-height: 0;
  overflow: hidden;
  background: #FBF6E9;
  border: 1px solid #e6dcd3;
  border-radius: 7px;
}

.compare-canvas-panel {
  box-shadow: inset 0 0 12px rgba(92, 63, 36, 0.05);
}

.canvas-heading {
  position: absolute;
  top: 8px;
  left: 12px;
  right: 12px;
  z-index: 2;
  pointer-events: none;
}

.canvas-heading span {
  display: block;
  overflow: hidden;
  color: #b22222;
  font-size: 15px;
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
  padding: 9px;
  box-shadow: 0 1px 5px rgba(90, 60, 35, 0.06);
}

.panel-title-row {
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px solid #d9cebf;
}

.panel-title-row strong {
  display: block;
  overflow: hidden;
  color: #b22222;
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
  color: #b35c37;
  font-size: 13px;
  font-weight: 900;
}

.compare-desc-list {
  flex: 1 1 auto;
  min-height: 0;
  padding-right: 3px;
  overflow-y: auto;
}

.compare-desc-card {
  padding: 8px;
  margin-bottom: 7px;
  color: #5c4636;
  font: 11px/1.5 "Microsoft YaHei", sans-serif;
  background: #fff;
  border: 1px solid #e6dcd3;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(90, 60, 35, 0.06);
}

.compare-desc-card.focused {
  padding: 10px;
  font-size: 12px;
}

.compare-desc-card h4 {
  margin: 0 0 5px;
  font-size: 13px;
  line-height: 1.2;
}

.compare-desc-card h4 small {
  color: #998370;
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
  color: #998370;
  font-style: italic;
}

.load-state {
  position: absolute;
  inset: 40px 12px 12px;
  z-index: 10;
  display: grid;
  place-items: center;
  color: #8b4513;
  font-size: 13px;
  font-weight: 800;
  text-align: center;
  background: rgba(253, 251, 247, 0.86);
}

.load-state.error {
  color: #b22222;
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
