<template>
  <PanelCard class="left-bottom-card" title="脸谱主题词云" eyebrow="行当意象与叙事关键词">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ChartOne v-if="view === 'a'" />
    <ChartTwo v-else />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

const view = ref('a')
</script>

<style scoped>
.left-bottom-card.panel-card {
  position: relative;
  display: flex;
  flex-direction: column;
  isolation: isolate;
  padding: 11px 10px 9px;
  overflow: hidden;
  border: 1px solid rgba(143, 47, 36, 0.54);
  border-radius: 2px;
  background:
    linear-gradient(180deg, rgba(255, 251, 241, 0.9), rgba(246, 235, 213, 0.78)),
    #f7edd8;
  box-shadow:
    inset 0 0 0 1px rgba(198, 121, 73, 0.13),
    0 0 0 1px rgba(255, 248, 232, 0.45);
}

.left-bottom-card.panel-card::before,
.left-bottom-card.panel-card::after {
  position: absolute;
  content: "";
  pointer-events: none;
}

.left-bottom-card.panel-card::before {
  inset: 5px;
  z-index: -1;
  border: 1px solid rgba(143, 47, 36, 0.16);
}

.left-bottom-card.panel-card::after {
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 24px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 1px 24px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 24px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 1px 24px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 24px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 1px 24px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 24px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 1px 24px no-repeat;
  opacity: 0.7;
}

.left-bottom-card :deep(.panel-card__header) {
  position: relative;
  z-index: 3;
  flex: 0 0 auto;
  min-height: 40px;
  margin-bottom: 4px;
  padding: 0 2px 6px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.3);
}

.left-bottom-card :deep(.panel-card__eyebrow) {
  margin: 0 0 3px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.1;
}

.left-bottom-card :deep(h2) {
  color: #5b1e17;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: 0;
}

.left-bottom-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  display: grid;
  flex: 1 1 auto;
  min-height: 0;
  place-items: center;
}

.left-bottom-card :deep(.chart-toggle) {
  position: relative;
  z-index: 4;
  width: 78px;
  height: 28px;
  border-color: rgba(143, 47, 36, 0.48);
  color: #7a241d;
  background: rgba(255, 249, 237, 0.78);
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.74);
}

.left-bottom-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 800;
}

.left-bottom-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}
</style>
