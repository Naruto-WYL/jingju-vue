<template>
  <PanelCard
    class="main-bottom-card"
    :class="{ 'main-bottom-card--river': view === 'a', 'main-bottom-card--summary': view === 'b' }"
  >
    <ChartToggle v-model="view" />

    <div class="main-bottom-content">
      <div class="river-rhythm-heading">剧情阶段识别与叙事节奏模式分析</div>
      <ChartOne v-if="view === 'a'" />
      <ChartTwo v-else />
    </div>
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  data: {
    type: Array,
    required: true,
  },
})

const view = ref('a')
</script>

<style scoped>
.main-bottom-card.panel-card {
  padding: 10px 15px 11px;
  font-family: "STKaiti", "KaiTi", serif;
}

.main-bottom-card :deep(*) {
  font-family: "STKaiti", "KaiTi", serif;
}

.main-bottom-card :deep(.panel-card__header) {
  align-items: flex-start;
  min-height: 30px;
  margin-bottom: 0;
  padding: 0 2px;
  border-bottom: 0;
}

.main-bottom-card--river :deep(.panel-card__header) {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  padding-right: 0;
}

.main-bottom-card--summary :deep(.panel-card__header) {
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  padding-right: 0;
}

.main-bottom-card :deep(.panel-card__body) {
  position: relative;
  display: block;
  height: 100%;
  min-height: 0;
  gap: 4px;
}

.main-bottom-card :deep(.chart-toggle) {
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
}

.main-bottom-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 12px;
  font-weight: 800;
}

.main-bottom-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}

.main-bottom-content {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding-top: 32px;
  box-sizing: border-box;
}

.river-rhythm-heading {
  position: absolute;
  top: 0;
  left: 0;
  right: 84px;
  z-index: 3;
  overflow: hidden;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
}
</style>
