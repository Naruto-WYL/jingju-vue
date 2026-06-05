<template>
  <PanelCard
    class="left-bottom-card"
    :class="{ 'left-bottom-card--network': view === 'a', 'left-bottom-card--structure': view === 'b' }"
    :title="panelTitle"
    eyebrow="角色关系网络"
  >
    <template #action>
      <div class="left-bottom-actions">
        <ChartToggle v-model="view" />
        <div v-show="view === 'a'" id="left-bottom-script-select-anchor" class="left-bottom-script-select-anchor" />
      </div>
    </template>

    <ChartOne v-if="view === 'a'" :arc-relations="arcRelations" select-target="#left-bottom-script-select-anchor" />
    <ChartTwo v-else :plays="plays" />
  </PanelCard>
</template>

<script setup>
import { computed, ref } from 'vue'
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
const panelTitle = computed(() => (view.value === 'a' ? '主要角色互动弧线图' : '角色关系网络结构特征'))
</script>

<style scoped>
.left-bottom-card.panel-card {
  position: relative;
  display: flex;
  flex-direction: column;
  isolation: isolate;
  padding: 14px 15px 13px;
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

.left-bottom-card.panel-card::before,
.left-bottom-card.panel-card::after {
  position: absolute;
  content: "";
  pointer-events: none;
}

.left-bottom-card.panel-card::before {
  inset: 5px;
  z-index: -1;
  border: 1px solid rgba(143, 47, 36, 0.2);
}

.left-bottom-card.panel-card::after {
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

.left-bottom-card :deep(.panel-card__header) {
  position: relative;
  z-index: 1;
  flex: 0 0 auto;
  align-items: flex-start;
  min-height: 53px;
  margin-bottom: 8px;
  padding: 0 2px 8px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.32);
}

.left-bottom-card--network :deep(.panel-card__header) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto minmax(0, 1fr);
  grid-template-rows: 20px 24px;
  column-gap: 4px;
  align-items: center;
  padding-right: 0;
}

.left-bottom-card--network :deep(.panel-card__header > div:first-child) {
  display: contents;
}

.left-bottom-card--network :deep(.panel-card__eyebrow) {
  grid-column: 1 / 3;
  grid-row: 1;
  justify-self: start;
}

.left-bottom-card :deep(.panel-card__eyebrow) {
  margin: 0 0 4px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.1;
}

.left-bottom-card :deep(h2) {
  color: #5b1e17;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 21px;
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: 0;
}

.left-bottom-card--network :deep(h2) {
  grid-column: 2;
  grid-row: 2;
  justify-self: end;
  font-size: 18px;
  text-align: center;
  white-space: nowrap;
}

.left-bottom-card--structure :deep(.panel-card__header) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  grid-template-rows: 20px 24px;
  align-items: center;
  padding-right: 0;
}

.left-bottom-card--structure :deep(.panel-card__header > div:first-child) {
  display: contents;
}

.left-bottom-card--structure :deep(.panel-card__eyebrow) {
  grid-column: 1 / 3;
  grid-row: 1;
  justify-self: start;
}

.left-bottom-card--structure :deep(h2) {
  grid-column: 2;
  grid-row: 2;
  justify-self: center;
  font-size: 18px;
  text-align: center;
  white-space: nowrap;
}

.left-bottom-card :deep(.panel-card__body) {
  position: relative;
  z-index: 1;
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
  gap: 4px;
}

.left-bottom-card :deep(.chart-toggle) {
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

.left-bottom-actions {
  position: static;
}

.left-bottom-card--network .left-bottom-actions {
  display: contents;
}

.left-bottom-script-select-anchor {
  z-index: 3;
  width: clamp(140px, 42%, 190px);
  height: 22px;
}

.left-bottom-card--network .left-bottom-script-select-anchor {
  grid-column: 3;
  grid-row: 2;
  justify-self: start;
}

.left-bottom-card--network :deep(.script-select) {
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
