<template>
  <PanelCard class="right-bottom-card" title="核心主题分析" eyebrow="核心主题、剧本组合与共现强度">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ThemeRingChartOne v-if="view === 'a'" />
    <ThemeRingChartTwo v-else />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ThemeRingChartOne from './ChartOne.vue'
import ThemeRingChartTwo from './ChartTwo.vue'

defineProps({
  data: {
    type: Array,
    required: true,
  },
})

const view = ref('a')
</script>

<style scoped>
.right-bottom-card.panel-card {
  padding: 14px 10px 10px;
}

.right-bottom-card :deep(.panel-card__header) {
  align-items: flex-start;
  min-height: 42px;
  margin-bottom: 6px;
  padding: 0 2px 7px;
  border-bottom-color: rgba(143, 47, 36, 0.3);
}

.right-bottom-card :deep(.panel-card__eyebrow) {
  margin: 0 0 4px;
  font-size: 13px;
}

.right-bottom-card :deep(h2) {
  font-size: 18px;
}

.right-bottom-card :deep(.panel-card__body) {
  min-height: 0;
  gap: 4px;
}

.right-bottom-card :deep(.chart-toggle) {
  position: relative;
  z-index: 4;
  width: 78px;
  height: 28px;
  border-color: rgba(143, 47, 36, 0.48);
  color: #7a241d;
  background: rgba(255, 249, 237, 0.78);
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.74);
}

.right-bottom-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 800;
}

.right-bottom-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}
</style>
