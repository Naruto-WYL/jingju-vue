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
  position: relative;
  display: flex;
  flex-direction: column;
  isolation: isolate;
  padding: 14px 10px 10px;
  overflow: hidden;
  border: 1px solid rgba(143, 47, 36, 0.58);
  border-radius: 2px;
  background:
    linear-gradient(180deg, rgba(255, 251, 241, 0.88), rgba(246, 235, 213, 0.76)),
    #f7edd8;
  box-shadow:
    inset 0 0 0 1px rgba(198, 121, 73, 0.14),
    0 0 0 1px rgba(255, 248, 232, 0.5);
}

.right-bottom-card.panel-card::before,
.right-bottom-card.panel-card::after {
  position: absolute;
  content: "";
  pointer-events: none;
}

.right-bottom-card.panel-card::before {
  inset: 5px;
  z-index: -1;
  border: 1px solid rgba(143, 47, 36, 0.2);
}

.right-bottom-card.panel-card::after {
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 1px 26px no-repeat;
  opacity: 0.72;
}

.right-bottom-card :deep(.panel-card__header) {
  position: relative;
  z-index: 3;
  flex: 0 0 auto;
  align-items: flex-start;
  min-height: 50px;
  margin-bottom: 8px;
  padding: 0 2px 8px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.32);
}

.right-bottom-card :deep(.panel-card__eyebrow) {
  margin: 0 0 4px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.1;
}

.right-bottom-card :deep(h2) {
  color: #5b1e17;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 21px;
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: 0;
}

.right-bottom-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  flex: 1 1 auto;
  height: auto;
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
