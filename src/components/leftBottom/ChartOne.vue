<template>
  <div class="arc-panel">
    <div class="arc-summary">
      <span>{{ arcRelations.playTitle || '代表剧目' }}</span>
      <strong>{{ arcRelations.nodes.length }} 个角色 / {{ arcRelations.links.length }} 条关系</strong>
    </div>

    <div class="mask-camp-row">
      <article v-for="camp in camps" :key="camp.id" class="mask-camp">
        <MiniMask />
        <i :style="{ background: camp.color }" />
      </article>
    </div>

    <svg class="arc-diagram" viewBox="0 0 640 330" role="img" aria-label="主要角色互动弧线图">
      <defs>
        <filter id="arcGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="#6f1418" flood-opacity="0.16" />
        </filter>
      </defs>

      <g class="arc-links">
        <path
          v-for="link in arcLinks"
          :key="link.id"
          :d="link.path"
          :stroke-width="link.width"
          :stroke-opacity="link.opacity"
        >
          <title>{{ link.sourceName }} - {{ link.targetName }}：互动 {{ link.weight }}</title>
        </path>
      </g>

      <g class="arc-nodes">
        <g v-for="node in arcNodes" :key="node.id" class="arc-node" :transform="`translate(${node.x}, ${baseY})`">
          <circle class="arc-dot" :r="node.radius" :fill="node.color" />
          <text y="18">{{ node.name }}</text>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const MiniMask = {
  template: `
    <svg class="mini-mask" viewBox="-22 -22 44 58" aria-hidden="true">
      <path class="mini-mask__face" d="M 0 -18 C 14 -17 20 -7 18 8 C 16 22 8 31 0 33 C -8 31 -16 22 -18 8 C -20 -7 -14 -17 0 -18 Z" />
      <path class="mini-mask__mark" d="M -4 -14 C -14 -8 -14 3 -6 10" />
      <path class="mini-mask__mark" d="M 4 -14 C 14 -8 14 3 6 10" />
      <circle class="mini-mask__eye" cx="-6" cy="4" r="2" />
      <circle class="mini-mask__eye" cx="6" cy="4" r="2" />
      <path class="mini-mask__mouth" d="M -5 16 Q 0 19 5 16" />
    </svg>
  `,
}

const props = defineProps({
  arcRelations: {
    type: Object,
    required: true,
  },
})

const baseY = 258
const campColors = ['#8b2a25', '#2f6f6d', '#c28732', '#4f5b7c', '#8a5b76']

const arcNodes = computed(() => {
  const nodes = props.arcRelations.nodes || []
  const step = nodes.length > 1 ? 560 / (nodes.length - 1) : 0

  return nodes.map((node, index) => ({
    ...node,
    x: 40 + index * step,
    radius: Math.max(6, Math.min(14, 6 + node.value / 45)),
    color: campColors[node.camp % campColors.length],
  }))
})

const arcLinks = computed(() => {
  const nodeMap = new Map(arcNodes.value.map((node) => [node.id, node]))
  const weights = (props.arcRelations.links || []).map((link) => link.weight)
  const maxWeight = Math.max(1, ...weights)

  return (props.arcRelations.links || [])
    .map((link, index) => {
      const source = nodeMap.get(link.source)
      const target = nodeMap.get(link.target)
      if (!source || !target) return null

      const distance = Math.abs(target.x - source.x)
      const strength = link.weight / maxWeight
      const arcHeight = 32 + distance * 0.22 + strength * 88
      const controlY = baseY - arcHeight
      const width = 0.8 + strength * 3.8

      return {
        id: `${link.source}-${link.target}-${index}`,
        sourceName: source.name,
        targetName: target.name,
        weight: link.weight,
        width,
        opacity: 0.18 + strength * 0.52,
        path: `M ${source.x} ${baseY} C ${source.x} ${controlY}, ${target.x} ${controlY}, ${target.x} ${baseY}`,
      }
    })
    .filter(Boolean)
})

const camps = computed(() => {
  const ids = Array.from(new Set(arcNodes.value.map((node) => node.camp))).slice(0, 5)
  return ids.map((id) => ({
    id,
    label: id + 1,
    color: campColors[id % campColors.length],
  }))
})
</script>

<style scoped>
.arc-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 6px;
  height: 100%;
  min-height: 0;
}

.arc-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 26px;
  padding: 5px 8px;
  border: 1px solid rgba(88, 68, 51, 0.12);
  border-radius: 6px;
  color: #5f5348;
  background: rgba(255, 255, 255, 0.42);
  font-size: 11px;
}

.arc-summary span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arc-summary strong {
  flex: 0 0 auto;
  color: #7b2723;
}

.arc-diagram {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: visible;
}

.arc-links path {
  fill: none;
  stroke: #a85c43;
  stroke-linecap: round;
  filter: url("#arcGlow");
  mix-blend-mode: multiply;
}

.arc-dot {
  stroke: #fff7ea;
  stroke-width: 2;
  filter: drop-shadow(0 2px 3px rgba(61, 47, 38, 0.24));
}

.arc-node text {
  fill: #352d27;
  font-size: 10px;
  text-anchor: middle;
  dominant-baseline: hanging;
}

.mask-camp-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  min-height: 54px;
  overflow: hidden;
  padding: 2px 4px 4px;
}

.mask-camp {
  display: inline-grid;
  justify-items: center;
  align-items: center;
  gap: 2px;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

.mask-camp i {
  width: 8px;
  height: 8px;
  border: 1.5px solid #fff7ea;
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(61, 47, 38, 0.22);
}

.mini-mask {
  width: 31px;
  height: 38px;
  flex: 0 0 auto;
}

.mini-mask :deep(.mini-mask__face) {
  fill: #fff7ea;
  stroke: rgba(88, 63, 48, 0.42);
  stroke-width: 1.2;
}

.mini-mask :deep(.mini-mask__mark) {
  fill: none;
  stroke: #9b2f2a;
  stroke-width: 2;
  stroke-linecap: round;
}

.mini-mask :deep(.mini-mask__eye) {
  fill: #2f2924;
}

.mini-mask :deep(.mini-mask__mouth) {
  fill: none;
  stroke: #2f2924;
  stroke-width: 1.3;
  stroke-linecap: round;
}
</style>
