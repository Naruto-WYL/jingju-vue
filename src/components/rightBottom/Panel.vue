<template>
  <PanelCard class="right-bottom-card">
    <ChartToggle v-model="view" />

    <div class="right-bottom-content">
      <div class="right-bottom-heading">剧本核心主题与组合模式分析</div>
      <ThemeRingChartOne v-if="view === 'a'" />
      <ThemeRingChartTwo v-else />
    </div>
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

.right-bottom-card :deep(.panel-card__body) {
  position: relative;
  display: block;
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
  gap: 4px;
}

.right-bottom-card :deep(.chart-toggle) {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 4;
  width: 96px;
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

.right-bottom-content {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding-top: 32px;
  box-sizing: border-box;
}

.right-bottom-heading {
  position: absolute;
  top: 0;
  left: 0;
  right: 84px;
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
</style>
