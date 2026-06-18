<template>
  <PanelCard class="left-bottom-card">
    <div class="left-bottom-content">
      <div class="pattern-mode-heading">行当云笺</div>
      <ChartOne v-if="view === 'a'" />
      <ChartTwo v-else />
    </div>
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'

import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

const view = ref('a')
</script>

<style scoped>
.left-bottom-card.panel-card {
  padding: 7px 6px 5px;
}

.left-bottom-card :deep(.panel-card__header) {
  flex: 0 0 auto;
  min-height: 30px;
}

.left-bottom-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  display: block;
  flex: 1 1 auto;
  min-height: 0;
}

.left-bottom-content {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding-top: 25px;
  box-sizing: border-box;
}

.pattern-mode-heading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
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
