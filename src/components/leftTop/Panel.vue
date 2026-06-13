<template>
  <PanelCard class="left-top-card" title="" eyebrow="" :style="cardStyle">
    <ChartToggle v-model="view" />

    <div ref="scaleHost" class="left-top-scale-host">
      <div class="pattern-mode-heading">角色-行当-时期对应模式</div>
      <ChartOne v-if="view === 'a'" :stats="stats" />
      <ChartTwo v-else />
    </div>
  </PanelCard>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

const MIN_DESIGN_WIDTH = 467
const DESIGN_HEIGHT = 711

defineProps({
  stats: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
const scaleHost = ref(null)
const leftTopScale = ref(1)
const leftTopContentWidth = ref(MIN_DESIGN_WIDTH)

const cardStyle = computed(() => ({
  '--left-top-scale': leftTopScale.value,
  '--left-top-content-width': `${leftTopContentWidth.value}px`,
}))

let resizeObserver = null

onMounted(async () => {
  await nextTick()
  updateScale()

  const body = scaleHost.value?.parentElement
  if (body) {
    resizeObserver = new ResizeObserver(updateScale)
    resizeObserver.observe(body)
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

function updateScale() {
  const body = scaleHost.value?.parentElement
  if (!body) return

  const { width, height } = body.getBoundingClientRect()
  const nextScale = Math.min(width / MIN_DESIGN_WIDTH, height / DESIGN_HEIGHT, 1)
  const boundedScale = Number(Math.max(nextScale, 0.1).toFixed(4))
  leftTopScale.value = boundedScale
  leftTopContentWidth.value = Math.max(MIN_DESIGN_WIDTH, Math.floor(width / boundedScale))
}
</script>

<style scoped>
.left-top-card.panel-card {
  display: block;
  padding: 14px 16px 13px;
}

.left-top-card :deep(.panel-card__header) {
  display: none;
}

.left-top-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  padding: 0;
  overflow: hidden;
}

.left-top-scale-host {
  position: relative;
  width: var(--left-top-content-width, 467px);
  height: 711px;
  padding-top: 32px;
  transform: scale(var(--left-top-scale, 1));
  transform-origin: top left;
}

.pattern-mode-heading {
  position: absolute;
  top: 0;
  left: 0px;
  right: 118px;
  z-index: 3;
  overflow: hidden;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}

.left-top-card :deep(.chart-toggle) {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 4;
  width: 78px;
  height: 28px;
  border-color: rgba(143, 47, 36, 0.48);
  color: #7a241d;
  background: rgba(255, 249, 237, 0.78);
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.74);
  pointer-events: auto;
}

.left-top-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 800;
}

.left-top-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}
</style>
