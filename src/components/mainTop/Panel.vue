<template>
  <PanelCard class="main-top-card">
    <div class="main-top-content">
      <div class="main-top-heading">角色关系—主题表达—叙事走向协同机制分析</div>
      <ChartOne v-if="view === 'a'" :graph="graph" />
      <ChartTwo v-else :graph="graph" />
    </div>
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  graph: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
</script>

<style scoped>
.main-top-card.panel-card {
  padding: 11px 10px 9px;
}

.main-top-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  display: block;
  flex: 1 1 auto;
  min-height: 0;
}

.main-top-content {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding-top: 32px;
  box-sizing: border-box;
}

.main-top-heading {
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
