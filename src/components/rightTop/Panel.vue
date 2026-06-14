<template>
  <PanelCard
    class="right-top-card"
    :class="{ 'right-top-card--network': view === 'a', 'right-top-card--structure': view === 'b' }"
  >
    <ChartToggle v-model="view" />

    <div class="right-top-content">
      <div class="right-top-heading">角色关系网络与结构特征分析</div>
      <div v-show="view === 'a'" id="right-top-script-select-anchor" class="right-top-script-select-anchor" />
      <ChartOne v-if="view === 'a'" :arc-relations="arcRelations" select-target="#right-top-script-select-anchor" />
      <ChartTwo v-else :plays="plays" />
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
  plays: {
    type: Array,
    required: true,
  },
  arcRelations: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
</script>

<style scoped>
.right-top-card.panel-card {
  padding: 14px 15px 14px;
}

.right-top-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  display: block;
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
  gap: 4px;
}

.right-top-card :deep(.chart-toggle) {
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

.right-top-card :deep(.chart-toggle span) {
  height: 22px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 800;
}

.right-top-card :deep(.chart-toggle .active) {
  color: #fff8ed;
  background: #8f2f24;
}

.right-top-content {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding-top: 32px;
  box-sizing: border-box;
}

.right-top-card--network .right-top-content {
  padding-top: 58px;
}

.right-top-heading {
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

.right-top-script-select-anchor {
  position: absolute;
  top: 30px;
  left: 50%;
  z-index: 3;
  width: clamp(140px, 42%, 190px);
  height: 22px;
  transform: translateX(-50%);
}

.right-top-card--network :deep(.script-select) {
  width: 100%;
  height: 22px;
  padding: 0 20px 0 6px;
  font-size: 13px;
  font-weight: 800;
  line-height: 20px;
  text-align: center;
  text-align-last: center;
}
</style>
