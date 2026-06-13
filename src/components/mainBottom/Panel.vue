<template>
  <PanelCard
    class="main-bottom-card"
    :class="{ 'main-bottom-card--river': view === 'a', 'main-bottom-card--summary': view === 'b' }"
  >
    <template #action>
      <div class="main-bottom-actions">
        <ChartToggle v-model="view" label-a="气韵推演" label-b="模式对比" />
      </div>
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
  height: calc(100% - 30px);
  min-height: 0;
  gap: 4px;
}

.main-bottom-card :deep(.chart-toggle) {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 4;
  width: 164px;
  height: 28px;
  border-color: rgba(143, 47, 36, 0.48);
  color: #7a241d;
  background: rgba(255, 249, 237, 0.78);
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.74);
}

.main-bottom-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 13px;
  font-weight: 800;
}

.main-bottom-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}

.main-bottom-actions {
  position: static;
}

.main-bottom-card--river .main-bottom-actions {
  display: block;
}
</style>
