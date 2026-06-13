<template>
  <PanelCard class="left-bottom-card">
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
  padding: 11px 10px 9px;
}

.left-bottom-card :deep(.panel-card__header) {
  flex: 0 0 auto;
  min-height: 30px;
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
