<template>
  <section class="mode-compare-shell">
    <div class="mode-compare-card">
      <div class="mode-legend" aria-label="综合剧情张力对比图例">
        <span class="legend-title">综合剧情张力 对比：</span>
        <div v-for="mode in modeProfiles" :key="mode.id" class="legend-item">
          <i :style="{ background: mode.color }"></i>{{ mode.shortName }}
        </div>
      </div>

      <div class="mode-grid">
        <div ref="canvasContainerRef" class="compare-canvas-panel">
          <div class="canvas-title">
            <strong>八大宏观叙事结构拓扑叠加</strong>
            <span>Integrated Narrative Tension / Mode Compare</span>
          </div>
          <canvas ref="canvasRef" class="compare-canvas"></canvas>

          <div ref="tooltipRef" class="compare-tooltip" :class="{ visible: isHovering }">
            <div class="tooltip-title">同期《综合张力》对比：</div>
            <div class="tooltip-grid">
              <div v-for="mode in modeProfiles" :key="mode.id" class="tooltip-row">
                <span :style="{ color: mode.color }">{{ mode.fullName }}</span>
                <strong :style="{ color: mode.color }">{{ Math.round(getModeValue(mode, globalProgress)) }}%</strong>
              </div>
            </div>
          </div>
        </div>

        <aside class="compare-analysis">
          <h3>典型叙事结构特征归纳</h3>
          <div class="scene-readout">
            <span>时间轴定位 (X轴)</span>
            <strong>叙事轴推演进度：{{ Math.floor(globalProgress * 100) }}%</strong>
          </div>

          <div class="desc-block">
            <span>宏观结构提炼：</span>
            <div class="mode-desc-list">
              <article v-for="(mode, index) in modeProfiles" :key="mode.id" class="mode-desc-item">
                <b :style="{ color: mode.color }">
                  {{ index + 1 }}. {{ mode.fullName }}（例：《{{ mode.typicalScript }}》）
                </b>
                <span>宏观：{{ mode.shape }}</span>
                <span>波纹：{{ mode.wave }}</span>
              </article>
            </div>
          </div>
        </aside>
      </div>

      <div class="timeline-row">
        <button class="mini-play-btn" type="button" @click="togglePlay" aria-label="播放模式对比">
          <svg class="play-icon" :class="{ hidden: isPlaying }" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
          <svg class="pause-icon" :class="{ hidden: !isPlaying }" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" /></svg>
        </button>
        <div class="progress-percent">{{ Math.floor(globalProgress * 100) }}%</div>
        <input
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
        {{ errorMessage || '叙事模式数据加载中...' }}
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { narrativeModeProfiles } from './narrativeModeProfiles'

const STAGES = ['开端', '发展', '转折', '高潮', '结局']
const AXIS_LABELS = ['开端', '发展', '转折', '高潮', '结局']

const canvasRef = ref(null)
const canvasContainerRef = ref(null)
const tooltipRef = ref(null)
const loading = ref(false)
const errorMessage = ref('')
const modeProfiles = ref(narrativeModeProfiles)
const globalProgress = ref(0)
const sliderValue = ref(0)
const isPlaying = ref(false)
const isHovering = ref(false)

let ctx = null
let animationFrameId = 0
let resizeHandler = null
let flowTime = 0
let trackerXCss = 0
let currentMouseY = 0
const layout = { paddingLeft: 60, paddingRight: 40, paddingTop: 64, paddingBottom: 42 }

const currentStageIndex = computed(() => Math.min(STAGES.length - 1, Math.floor(globalProgress.value * STAGES.length)))

onMounted(async () => {
  await nextTick()
  initCanvas()
  attachHoverEvents()
  animate()
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
})

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
  const container = canvasContainerRef.value
  if (!canvas || !container || !ctx) return

  const rect = container.getBoundingClientRect()
  if (!rect.width || !rect.height) return

  const ratio = window.devicePixelRatio || 1
  canvas.width = rect.width * ratio
  canvas.height = rect.height * ratio
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
}

function attachHoverEvents() {
  const container = canvasContainerRef.value
  if (!container) return

  container.addEventListener('mousemove', (event) => {
    const rect = container.getBoundingClientRect()
    currentMouseY = event.clientY - rect.top
    const mouseX = event.clientX - rect.left
    isHovering.value = Math.abs(mouseX - trackerXCss) < 30

    if (isHovering.value) {
      const leftPos = trackerXCss + 228 > rect.width ? trackerXCss - 232 : trackerXCss + 16
      if (tooltipRef.value) {
        tooltipRef.value.style.left = `${Math.max(8, leftPos)}px`
        tooltipRef.value.style.top = `${Math.max(10, Math.min(currentMouseY - 30, rect.height - 168))}px`
      }
    }
  })

  container.addEventListener('mouseleave', () => {
    isHovering.value = false
  })
}

function animate() {
  if (isPlaying.value) {
    globalProgress.value += 0.0006
    if (globalProgress.value >= 1) {
      globalProgress.value = 0
      sliderValue.value = 0
      isPlaying.value = false
    } else {
      sliderValue.value = globalProgress.value * 100
    }
  }

  drawCompare()
  animationFrameId = requestAnimationFrame(animate)
}

function drawCompare() {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !ctx) return

  const ratio = window.devicePixelRatio || 1
  const rect = container.getBoundingClientRect()
  if (canvas.width !== rect.width * ratio || canvas.height !== rect.height * ratio) resizeCanvas()

  const w = canvas.width / ratio
  const h = canvas.height / ratio
  if (!w || !h) return

  const graphW = w - layout.paddingLeft - layout.paddingRight
  const graphH = h - layout.paddingTop - layout.paddingBottom
  const baseY = h - layout.paddingBottom
  const currentTrackerX = layout.paddingLeft + globalProgress.value * graphW
  trackerXCss = currentTrackerX
  flowTime += 0.018

  ctx.clearRect(0, 0, w, h)
  drawAxes(w, graphW, graphH, baseY)

  modeProfiles.value.forEach((mode) => {
    const points = []
    const segmentEndX = Math.max(layout.paddingLeft + 2, currentTrackerX)
    for (let xPixel = layout.paddingLeft; xPixel <= segmentEndX; xPixel += 2) {
      const relativeX = (xPixel - layout.paddingLeft) / graphW
      const val = getModeValue(mode, relativeX)
      const ripple = getModeRipple(mode.key, xPixel, relativeX, val)
      points.push({
        x: xPixel,
        y: Math.min(baseY, baseY - (val * graphH / 100) + ripple),
      })
    }

    if (!points.length) return

    ctx.beginPath()
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y)
      else ctx.lineTo(point.x, point.y)
    })
    ctx.strokeStyle = mode.color
    ctx.lineWidth = 2.6
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.shadowColor = mode.color
    ctx.shadowBlur = 3
    ctx.stroke()
    ctx.shadowBlur = 0
  })

  ctx.strokeStyle = isHovering.value ? 'rgba(160, 82, 45, 0.9)' : 'rgba(160, 82, 45, 0.4)'
  ctx.lineWidth = isHovering.value ? 2.4 : 1.5
  ctx.setLineDash(isHovering.value ? [] : [5, 5])
  ctx.beginPath()
  ctx.moveTo(currentTrackerX, layout.paddingTop - 14)
  ctx.lineTo(currentTrackerX, baseY)
  ctx.stroke()
  ctx.setLineDash([])
}

function drawAxes(w, graphW, graphH, baseY) {
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  ctx.font = '11px sans-serif'
  ctx.lineWidth = 1

  ;[25, 50, 75, 100].forEach((val) => {
    const y = baseY - (val * graphH / 100)
    ctx.strokeStyle = 'rgba(160, 82, 45, 0.06)'
    ctx.beginPath()
    ctx.moveTo(layout.paddingLeft, y)
    ctx.lineTo(w - layout.paddingRight, y)
    ctx.stroke()
    ctx.fillStyle = '#A69482'
    ctx.fillText(`${val}%`, layout.paddingLeft - 8, y)
  })

  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  const activeIndex = Math.min(AXIS_LABELS.length - 1, Math.floor(globalProgress.value * AXIS_LABELS.length))
  AXIS_LABELS.forEach((label, index) => {
    const ratio = index / (AXIS_LABELS.length - 1)
    const x = layout.paddingLeft + ratio * graphW
    const isActive = index === activeIndex
    ctx.strokeStyle = isActive ? 'rgba(178, 34, 34, 0.36)' : 'rgba(28, 28, 28, 0.15)'
    ctx.beginPath()
    ctx.moveTo(x, layout.paddingTop - 8)
    ctx.lineTo(x, baseY + 6)
    ctx.stroke()
    ctx.fillStyle = isActive ? '#b22222' : '#998370'
    ctx.font = isActive ? 'bold 13px sans-serif' : '12px sans-serif'
    ctx.fillText(label, x, baseY + 8)
  })

  ctx.strokeStyle = '#D9CEBF'
  ctx.beginPath()
  ctx.moveTo(layout.paddingLeft, baseY)
  ctx.lineTo(w - layout.paddingRight, baseY)
  ctx.stroke()
}

function getModeValue(mode, progress) {
  const curve = mode?.displayCurve || mode?.curve || []
  if (!curve.length) return 0
  const safeProgress = Math.max(0, Math.min(1, progress))
  const floatIndex = safeProgress * (curve.length - 1)
  const leftIndex = Math.floor(floatIndex)
  const rightIndex = Math.min(leftIndex + 1, curve.length - 1)
  const t = floatIndex - leftIndex
  const smoothT = t * t * (3 - 2 * t)
  return curve[leftIndex] + (curve[rightIndex] - curve[leftIndex]) * smoothT
}

function getModeRipple(key, xPixel, relativeX, val) {
  if (key === 'singlePeak') return Math.sin(xPixel * 0.02 - flowTime * 1.5) * (val > 75 ? 60 : 10) * 0.15 * (val / 100)
  if (key === 'multiPeak') return Math.sin(xPixel * 0.08 - flowTime * 3.5) * 12 * (val / 100) + Math.cos(xPixel * 0.18 + flowTime) * 4
  if (key === 'crescendo') return Math.sin(xPixel * 0.04 - flowTime) * 8 * (val / 100)
  if (key === 'lateClimax') return relativeX > 0.75 ? Math.sin(xPixel * 0.25 - flowTime * 6) * 25 * (val / 100) + Math.cos(xPixel * 0.4) * 8 : Math.sin(xPixel * 0.01 - flowTime * 0.2)
  if (key === 'initialBurst') return relativeX < 0.25 ? Math.sin(xPixel * 0.1 - flowTime * 4) * 20 * (val / 100) : Math.sin(xPixel * 0.02 - flowTime) * 3
  if (key === 'endingBurst') return relativeX > 0.85 ? Math.sin(xPixel * 0.3 - flowTime * 8) * 30 * (val / 100) : Math.sin(xPixel * 0.01) * 0.5
  if (key === 'flatSmooth') return Math.sin(xPixel * 0.03 - flowTime * 0.8) * 3
  if (key === 'condensed') return relativeX > 0.4 && relativeX < 0.6 ? Math.sin(xPixel * 0.2 - flowTime * 5) * 20 : Math.sin(xPixel * 0.05 - flowTime) * 5
  return 0
}

function getModeStageText(mode) {
  const stageIndex = currentStageIndex.value
  const stage = STAGES[stageIndex]
  const conflict = mode.stageConflicts[stageIndex]
  const value = Math.round(getModeValue(mode, globalProgress.value))
  const examples = mode.examples.length ? `代表剧目：${mode.examples.join('、')}。` : ''
  return `${stage}阶段以“${conflict}”为高频主冲突，当前平均综合强度${value}%。${mode.feature}${examples}`
}

function handleSliderChange(value) {
  globalProgress.value = Math.max(0, Math.min(1, Number(value) / 100))
  sliderValue.value = globalProgress.value * 100
}

function togglePlay() {
  if (!isPlaying.value && globalProgress.value >= 1) {
    globalProgress.value = 0
    sliderValue.value = 0
  }
  isPlaying.value = !isPlaying.value
}

</script>

<style scoped>
.mode-compare-shell {
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #4a3b32;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.mode-compare-card {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 8px;
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
}

.mode-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  min-height: 28px;
  padding-right: 178px;
  color: #4a3b32;
  font-size: 11px;
  font-weight: 800;
}

.legend-title {
  color: #7a241d;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.legend-item i {
  width: 9px;
  height: 9px;
  border-radius: 2px;
}

.mode-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.35fr) minmax(300px, 1fr);
  gap: 8px;
  min-height: 0;
}

.compare-canvas-panel {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #e6dcd3;
  border-radius: 8px;
  background: #fdfbf7;
  box-shadow: inset 0 2px 12px rgba(93, 72, 53, 0.05);
}

.canvas-title {
  position: absolute;
  top: 10px;
  left: 16px;
  right: 16px;
  z-index: 2;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none;
}

.canvas-title strong {
  color: #b22222;
  font-size: 18px;
  line-height: 1.2;
  letter-spacing: 0;
}

.canvas-title span {
  color: #a69482;
  font-family: Consolas, "Microsoft YaHei", sans-serif;
  font-size: 10px;
  letter-spacing: 0;
}

.compare-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.compare-tooltip {
  position: absolute;
  z-index: 5;
  width: 210px;
  padding: 10px;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 28px rgba(93, 72, 53, 0.14);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.compare-tooltip.visible {
  opacity: 1;
}

.tooltip-title {
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e6dcd3;
  color: #a0522d;
  font-size: 12px;
  font-weight: 900;
}

.tooltip-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 4px;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 10px;
}

.tooltip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.compare-analysis {
  display: flex;
  min-height: 0;
  height: 100%;
  flex-direction: column;
  padding: 10px;
  border: 1px solid #d9cebf;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-sizing: border-box;
}

.compare-analysis h3 {
  margin: 0 0 6px;
  padding-bottom: 5px;
  border-bottom: 1px solid #d9cebf;
  color: #b22222;
  font-size: 14px;
  font-weight: 900;
  line-height: 1.2;
}

.scene-readout {
  margin-bottom: 6px;
  padding: 6px 8px;
  border: 1px solid #f5efe6;
  border-radius: 6px;
  background: #fdfbf7;
}

.scene-readout span,
.desc-block > span {
  display: block;
  margin-bottom: 3px;
  color: #998370;
  font-size: 10px;
  font-weight: 800;
}

.scene-readout strong {
  display: block;
  color: #4a3b32;
  font-size: 11px;
  line-height: 1.25;
}

.desc-block {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
}

.desc-block > span {
  color: #a0522d;
  font-size: 11px;
}

.mode-desc-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 6px;
  color: #5c4636;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 9.2px;
  line-height: 1.25;
  text-align: justify;
}

.mode-desc-list::-webkit-scrollbar {
  width: 5px;
}

.mode-desc-list::-webkit-scrollbar-track {
  background: rgba(245, 239, 230, 0.75);
  border-radius: 999px;
}

.mode-desc-list::-webkit-scrollbar-thumb {
  background: rgba(160, 82, 45, 0.42);
  border-radius: 999px;
}

.mode-desc-item {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1px;
  margin: 0 0 4px;
  padding-bottom: 3px;
  border-bottom: 1px dotted rgba(160, 82, 45, 0.15);
}

.mode-desc-item b {
  font-size: 10px;
  line-height: 1.2;
}

.mode-desc-item span {
  display: block;
}

.timeline-row {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 36px;
  padding: 0 2px;
}

.mini-play-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  color: #ffffff;
  background: #a0522d;
  cursor: pointer;
  box-shadow: 0 5px 12px rgba(80, 45, 25, 0.18);
}

.play-icon,
.pause-icon {
  width: 15px;
  height: 15px;
  fill: currentColor;
}

.play-icon {
  margin-left: 2px;
}

.hidden {
  display: none;
}

.progress-percent {
  width: 42px;
  color: #b22222;
  font-family: Consolas, "Microsoft YaHei", sans-serif;
  font-size: 12px;
  font-weight: 900;
  text-align: right;
}

.timeline-slider {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #e6dcd3;
  accent-color: #a0522d;
  cursor: pointer;
}

.timeline-slider::-webkit-slider-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #a0522d;
  box-shadow: 0 0 0 3px rgba(160, 82, 45, 0.14);
}

.load-state {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: grid;
  place-items: center;
  color: #7a6658;
  background: rgba(255, 250, 242, 0.78);
  font-size: 13px;
  font-weight: 800;
}

.load-state.error {
  color: #8b2a25;
}

:global(.single-preview-panel--main-bottom) .mode-compare-card {
  gap: 12px;
}

:global(.single-preview-panel--main-bottom) .mode-grid {
  grid-template-columns: minmax(0, 2.35fr) minmax(360px, 1fr);
  gap: 20px;
}

:global(.single-preview-panel--main-bottom) .mode-legend {
  min-height: 34px;
  padding-right: 184px;
  font-size: 13px;
}

:global(.single-preview-panel--main-bottom) .compare-analysis {
  padding: 14px;
}

:global(.single-preview-panel--main-bottom) .compare-analysis h3 {
  font-size: 16px;
  margin-bottom: 8px;
}

:global(.single-preview-panel--main-bottom) .mode-desc-list {
  overflow-y: auto;
  font-size: 10.5px;
  line-height: 1.32;
}

:global(.single-preview-panel--main-bottom) .mode-desc-item {
  margin-bottom: 5px;
}

:global(.single-preview-panel--main-bottom) .mode-desc-item b {
  font-size: 11px;
}

:global(.single-preview-panel--main-bottom) .timeline-row {
  height: 44px;
}

@media (max-width: 900px) {
  .mode-legend {
    justify-content: flex-start;
    flex-wrap: wrap;
    padding-right: 0;
  }

  .mode-grid {
    grid-template-columns: 1fr;
  }
}
</style>
