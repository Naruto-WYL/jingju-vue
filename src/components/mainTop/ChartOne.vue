<template>
  <div class="flow-card" @mouseleave="hideTooltip">
    <svg class="flow-svg" viewBox="0 0 820 420" role="img" aria-label="角色-主题-叙事协同演化图">
      <defs>
        <linearGradient
          v-for="link in layoutLinks"
          :id="link.gradientId"
          :key="link.gradientId"
          gradientUnits="userSpaceOnUse"
          :x1="link.source.x + link.source.w / 2"
          :y1="link.source.y"
          :x2="link.target.x - link.target.w / 2"
          :y2="link.target.y"
        >
          <stop offset="0%" :stop-color="link.sourceColor" stop-opacity="0.92" />
          <stop offset="100%" :stop-color="link.targetColor" stop-opacity="0.74" />
        </linearGradient>

        <filter id="softGlow" x="-30%" y="-50%" width="160%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#7cc7ff" flood-opacity="0.32" />
        </filter>
      </defs>

      <rect class="flow-bg" width="820" height="420" rx="18" @click="clearSelection" />
      <g class="grid-lines">
        <path v-for="x in gridXs" :key="`v-${x}`" :d="`M ${x} 32 L ${x} 390`" />
        <path v-for="y in gridYs" :key="`h-${y}`" :d="`M 24 ${y} L 796 ${y}`" />
      </g>
      <circle class="glow glow-a" cx="135" cy="70" r="118" />
      <circle class="glow glow-b" cx="650" cy="330" r="132" />

      <text class="chart-title" x="26" y="30">角色—主题—叙事协同演化图</text>
      <text class="chart-subtitle" x="26" y="50">角色关系层 → 主题表达层 → 叙事阶段层 → 关系演化层</text>

      <g class="layer-titles">
        <g v-for="layer in layoutLayers" :key="layer.key">
          <line class="layer-divider" :x1="layer.x" y1="66" :x2="layer.x" y2="370" />
          <text :x="layer.x" y="78">{{ layer.name }}</text>
        </g>
      </g>

      <g class="flow-links">
        <path
          v-for="link in layoutLinks"
          :key="link.id"
          class="flow-link"
          :class="{ active: isLinkActive(link), dimmed: isDimmedLink(link) }"
          :d="link.path"
          :stroke="`url(#${link.gradientId})`"
          :stroke-width="link.width"
          :stroke-opacity="link.opacity"
          @mouseenter="showLinkTooltip(link, $event)"
          @mousemove="moveTooltip($event)"
          @mouseleave="hideTooltip"
        />
      </g>

      <g class="flow-nodes">
        <g
          v-for="node in layoutNodes"
          :key="node.id"
          class="flow-node"
          :class="{ active: isNodeActive(node.id), selected: selectedNodeId === node.id, dimmed: isDimmedNode(node.id) }"
          :transform="`translate(${node.x}, ${node.y})`"
          @mouseenter="showNodeTooltip(node, $event)"
          @mousemove="moveTooltip($event)"
          @mouseleave="hideTooltip"
          @click.stop="toggleNode(node.id)"
        >
          <rect
            :x="-node.w / 2"
            :y="-node.h / 2"
            :width="node.w"
            :height="node.h"
            :rx="node.h / 2"
            :fill="node.fill"
          />
          <text class="node-name" y="-4">{{ node.name }}</text>
          <text class="node-value" y="13">强度 {{ node.value }}</text>
        </g>
      </g>

      <g class="legend">
        <g v-for="(item, index) in legendItems" :key="item.type" :transform="`translate(${560 + index * 62}, 386)`">
          <rect width="12" height="8" rx="4" :fill="item.color" />
          <text x="17" y="8">{{ item.name }}</text>
        </g>
      </g>
    </svg>

    <aside v-if="selectedNode" class="detail-panel">
      <button type="button" @click="clearSelection">×</button>
      <p>{{ layerNameMap[selectedNode.type] }}</p>
      <h3>{{ selectedNode.name }}</h3>
      <dl>
        <dt>强度值</dt>
        <dd>{{ selectedNode.value }}</dd>
        <dt>关联节点</dt>
        <dd>{{ selectedRelatedNodes.length }}</dd>
      </dl>
      <span>{{ selectedAnalysis }}</span>
    </aside>

    <div v-if="tooltip.show" class="flow-tooltip" :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }">
      <strong>{{ tooltip.title }}</strong>
      <span v-for="line in tooltip.lines" :key="line">{{ line }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'

defineProps({
  graph: {
    type: Object,
    required: false,
    default: () => ({ nodes: [], links: [] }),
  },
})

const width = 820
const columnXs = [92, 305, 510, 708]

const layerStyles = {
  relation: { color: '#6f7dff', fill: 'rgba(101, 115, 245, 0.26)' },
  theme: { color: '#f0b44c', fill: 'rgba(240, 180, 76, 0.27)' },
  narrative: { color: '#39c59b', fill: 'rgba(57, 197, 155, 0.24)' },
  evolution: { color: '#e7659b', fill: 'rgba(231, 101, 155, 0.25)' },
}

const layers = [
  {
    key: 'relation',
    name: '角色关系层',
    nodes: [
      { id: 'r1', name: '君臣关系', value: 92, type: 'relation' },
      { id: 'r2', name: '父子关系', value: 73, type: 'relation' },
      { id: 'r3', name: '夫妻关系', value: 65, type: 'relation' },
      { id: 'r4', name: '敌对关系', value: 88, type: 'relation' },
      { id: 'r5', name: '师徒关系', value: 51, type: 'relation' },
      { id: 'r6', name: '结义关系', value: 59, type: 'relation' },
    ],
  },
  {
    key: 'theme',
    name: '主题表达层',
    nodes: [
      { id: 't1', name: '忠义', value: 95, type: 'theme' },
      { id: 't2', name: '孝道', value: 72, type: 'theme' },
      { id: 't3', name: '爱情', value: 68, type: 'theme' },
      { id: 't4', name: '家国', value: 89, type: 'theme' },
      { id: 't5', name: '正邪', value: 84, type: 'theme' },
      { id: 't6', name: '牺牲', value: 61, type: 'theme' },
      { id: 't7', name: '团圆', value: 48, type: 'theme' },
    ],
  },
  {
    key: 'narrative',
    name: '叙事阶段层',
    nodes: [
      { id: 'n1', name: '开端', value: 45, type: 'narrative' },
      { id: 'n2', name: '发展', value: 72, type: 'narrative' },
      { id: 'n3', name: '转折', value: 86, type: 'narrative' },
      { id: 'n4', name: '高潮', value: 98, type: 'narrative' },
      { id: 'n5', name: '结局', value: 63, type: 'narrative' },
    ],
  },
  {
    key: 'evolution',
    name: '关系演化层',
    nodes: [
      { id: 'e1', name: '建立', value: 52, type: 'evolution' },
      { id: 'e2', name: '试探', value: 46, type: 'evolution' },
      { id: 'e3', name: '冲突', value: 82, type: 'evolution' },
      { id: 'e4', name: '决裂', value: 76, type: 'evolution' },
      { id: 'e5', name: '对抗', value: 91, type: 'evolution' },
      { id: 'e6', name: '和解', value: 64, type: 'evolution' },
      { id: 'e7', name: '重组', value: 58, type: 'evolution' },
    ],
  },
]

const links = [
  { source: 'r1', target: 't1', value: 95, label: '君臣关系强化忠义表达' },
  { source: 'r1', target: 't4', value: 88, label: '君臣关系承载家国秩序' },
  { source: 'r2', target: 't2', value: 78, label: '父子关系承载孝道伦理' },
  { source: 'r3', target: 't3', value: 74, label: '夫妻关系承载爱情忠贞' },
  { source: 'r4', target: 't5', value: 91, label: '敌对关系推动正邪冲突' },
  { source: 'r4', target: 't6', value: 65, label: '敌对关系引出牺牲主题' },
  { source: 't1', target: 'n4', value: 92, label: '忠义主题在高潮阶段集中爆发' },
  { source: 't4', target: 'n3', value: 82, label: '家国主题推动剧情转折' },
  { source: 't5', target: 'n4', value: 89, label: '正邪主题形成高潮对抗' },
  { source: 't2', target: 'n3', value: 71, label: '孝道主题常通过转折体现' },
  { source: 't3', target: 'n2', value: 69, label: '爱情主题推动剧情发展' },
  { source: 't7', target: 'n5', value: 58, label: '团圆主题多出现在结局' },
  { source: 'n1', target: 'e1', value: 54, label: '开端阶段建立人物关系' },
  { source: 'n2', target: 'e3', value: 72, label: '发展阶段产生冲突' },
  { source: 'n3', target: 'e4', value: 81, label: '转折阶段造成关系决裂' },
  { source: 'n4', target: 'e5', value: 96, label: '高潮阶段形成正面对抗' },
  { source: 'n5', target: 'e6', value: 66, label: '结局阶段走向和解' },
  { source: 'n5', target: 'e7', value: 61, label: '结局阶段完成关系重组' },
]

const hoveredNodeId = ref('')
const hoveredLinkId = ref('')
const selectedNodeId = ref('')
const tooltip = reactive({ show: false, x: 0, y: 0, title: '', lines: [] })

const layerNameMap = {
  relation: '角色关系层',
  theme: '主题表达层',
  narrative: '叙事阶段层',
  evolution: '关系演化层',
}

const gridXs = [170, 250, 390, 590, 735]
const gridYs = [100, 160, 220, 280, 340]
const legendItems = Object.entries(layerStyles).map(([type, style]) => ({
  type,
  name: layerNameMap[type],
  color: style.color,
}))

const layoutLayers = computed(() =>
  layers.map((layer, index) => ({
    ...layer,
    x: columnXs[index],
  })),
)

const layoutNodes = computed(() => {
  return layers.flatMap((layer, layerIndex) => {
    const top = 112
    const available = 242
    const step = layer.nodes.length > 1 ? available / (layer.nodes.length - 1) : 0
    return layer.nodes.map((node, nodeIndex) => {
      const h = 34 + (node.value / 100) * 10
      const w = 94 + (node.value / 100) * 30
      const offset = layerIndex % 2 ? 8 : 0

      return {
        ...node,
        x: columnXs[layerIndex],
        y: top + step * nodeIndex + offset,
        w,
        h,
        fill: layerStyles[node.type].fill,
      }
    })
  })
})

const nodeMap = computed(() => Object.fromEntries(layoutNodes.value.map((node) => [node.id, node])))

const layoutLinks = computed(() =>
  links.map((link, index) => {
    const source = nodeMap.value[link.source]
    const target = nodeMap.value[link.target]
    const sx = source.x + source.w / 2
    const sy = source.y
    const tx = target.x - target.w / 2
    const ty = target.y
    const bend = Math.max(62, (tx - sx) * 0.48)

    return {
      ...link,
      id: `${link.source}-${link.target}-${index}`,
      source,
      target,
      width: 1.5 + (link.value / 100) * 6.5,
      opacity: 0.18 + (link.value / 100) * 0.52,
      sourceColor: layerStyles[source.type].color,
      targetColor: layerStyles[target.type].color,
      gradientId: `flow-gradient-${index}`,
      path: `M ${sx} ${sy} C ${sx + bend} ${sy}, ${tx - bend} ${ty}, ${tx} ${ty}`,
    }
  }),
)

const activeNodeId = computed(() => selectedNodeId.value || hoveredNodeId.value)
const activeNodeSet = computed(() => {
  if (!activeNodeId.value) return new Set()
  const ids = new Set([activeNodeId.value])
  layoutLinks.value.forEach((link) => {
    if (link.source.id === activeNodeId.value || link.target.id === activeNodeId.value) {
      ids.add(link.source.id)
      ids.add(link.target.id)
    }
  })
  return ids
})

const activeLinkSet = computed(() => {
  if (!activeNodeId.value && !hoveredLinkId.value) return new Set()
  return new Set(
    layoutLinks.value
      .filter((link) => {
        if (hoveredLinkId.value && link.id === hoveredLinkId.value) return true
        return link.source.id === activeNodeId.value || link.target.id === activeNodeId.value
      })
      .map((link) => link.id),
  )
})

const selectedNode = computed(() => layoutNodes.value.find((node) => node.id === selectedNodeId.value))
const selectedRelatedNodes = computed(() => {
  if (!selectedNode.value) return []
  return layoutLinks.value
    .filter((link) => link.source.id === selectedNode.value.id || link.target.id === selectedNode.value.id)
    .map((link) => (link.source.id === selectedNode.value.id ? link.target : link.source))
})
const selectedAnalysis = computed(() => {
  if (!selectedNode.value) return ''
  if (selectedNode.value.type === 'theme') return `${selectedNode.value.name}主题通过角色关系与叙事阶段相连，显示主题表达如何推动关系演化。`
  if (selectedNode.value.type === 'relation') return `${selectedNode.value.name}是主题生成的重要入口，通常向忠义、家国、正邪等主题扩散。`
  if (selectedNode.value.type === 'narrative') return `${selectedNode.value.name}阶段承接主题张力，并将其转化为关系冲突、对抗或和解。`
  return `${selectedNode.value.name}体现人物关系在叙事推进后的结果状态。`
})

function isNodeActive(id) {
  return activeNodeSet.value.has(id) || layoutLinks.value.some((link) => link.id === hoveredLinkId.value && (link.source.id === id || link.target.id === id))
}

function isDimmedNode(id) {
  return Boolean(activeNodeId.value || hoveredLinkId.value) && !isNodeActive(id)
}

function isLinkActive(link) {
  return activeLinkSet.value.has(link.id)
}

function isDimmedLink(link) {
  return Boolean(activeNodeId.value || hoveredLinkId.value) && !isLinkActive(link)
}

function showNodeTooltip(node, event) {
  hoveredNodeId.value = node.id
  tooltip.title = node.name
  tooltip.lines = [`类型：${layerNameMap[node.type]}`, `强度：${node.value}`, `关联节点：${relatedCount(node.id)}`]
  moveTooltip(event)
  tooltip.show = true
}

function showLinkTooltip(link, event) {
  hoveredLinkId.value = link.id
  tooltip.title = `${link.source.name} → ${link.target.name}`
  tooltip.lines = [`关联强度：${link.value}`, `解释：${link.label}`]
  moveTooltip(event)
  tooltip.show = true
}

function moveTooltip(event) {
  const rect = event.currentTarget.ownerSVGElement?.getBoundingClientRect?.() || event.currentTarget.getBoundingClientRect()
  tooltip.x = event.clientX - rect.left + 12
  tooltip.y = event.clientY - rect.top + 12
}

function hideTooltip() {
  hoveredNodeId.value = ''
  hoveredLinkId.value = ''
  tooltip.show = false
}

function toggleNode(id) {
  selectedNodeId.value = selectedNodeId.value === id ? '' : id
}

function clearSelection() {
  selectedNodeId.value = ''
}

function relatedCount(id) {
  return layoutLinks.value.filter((link) => link.source.id === id || link.target.id === id).length
}
</script>

<style scoped>
.flow-card {
  position: relative;
  height: 100%;
  min-height: 0;
  border-radius: 10px;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 18%, rgba(83, 110, 255, 0.22), transparent 24%),
    radial-gradient(circle at 78% 78%, rgba(231, 101, 155, 0.18), transparent 26%),
    linear-gradient(135deg, #101827 0%, #172033 52%, #121827 100%);
}

.flow-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.flow-bg {
  fill: transparent;
}

.grid-lines path {
  stroke: rgba(214, 225, 255, 0.07);
  stroke-width: 1;
}

.glow {
  fill: rgba(255, 255, 255, 0.08);
  filter: blur(8px);
}

.chart-title {
  fill: #f3f7ff;
  font-size: 18px;
  font-weight: 800;
}

.chart-subtitle {
  fill: rgba(230, 238, 255, 0.62);
  font-size: 11px;
}

.layer-titles text {
  fill: rgba(238, 244, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
  text-anchor: middle;
}

.layer-divider {
  stroke: rgba(238, 244, 255, 0.08);
  stroke-width: 1;
}

.flow-link {
  fill: none;
  stroke-linecap: round;
  stroke-dasharray: 10 16;
  animation: flowMove 1.8s linear infinite;
  transition: opacity 0.18s ease, stroke-width 0.18s ease;
}

.flow-link.active {
  stroke-opacity: 0.9;
  filter: url("#softGlow");
}

.flow-link.dimmed {
  stroke-opacity: 0.05;
}

.flow-node rect {
  stroke: rgba(225, 237, 255, 0.42);
  stroke-width: 1;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.26));
  transition: opacity 0.18s ease, stroke-width 0.18s ease, filter 0.18s ease;
}

.flow-node text {
  pointer-events: none;
  text-anchor: middle;
}

.node-name {
  fill: #f8fbff;
  font-size: 12px;
  font-weight: 800;
}

.node-value {
  fill: rgba(241, 247, 255, 0.74);
  font-size: 10px;
}

.flow-node.active rect,
.flow-node.selected rect {
  stroke: rgba(255, 255, 255, 0.92);
  stroke-width: 2;
  filter: url("#softGlow");
}

.flow-node.dimmed {
  opacity: 0.22;
}

.legend text {
  fill: rgba(233, 240, 255, 0.72);
  font-size: 10px;
}

.detail-panel {
  position: absolute;
  right: 10px;
  top: 60px;
  width: 184px;
  padding: 12px;
  border: 1px solid rgba(218, 232, 255, 0.18);
  border-radius: 10px;
  color: #eef5ff;
  background: rgba(11, 18, 31, 0.78);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.24);
  backdrop-filter: blur(8px);
}

.detail-panel button {
  position: absolute;
  right: 8px;
  top: 6px;
  border: 0;
  color: rgba(238, 245, 255, 0.72);
  background: transparent;
  cursor: pointer;
}

.detail-panel p,
.detail-panel h3 {
  margin: 0;
}

.detail-panel p {
  color: #86d7ff;
  font-size: 11px;
  font-weight: 700;
}

.detail-panel h3 {
  margin-top: 5px;
  font-size: 17px;
}

.detail-panel dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 5px 9px;
  margin: 10px 0;
  font-size: 11px;
}

.detail-panel dt {
  color: rgba(238, 245, 255, 0.58);
}

.detail-panel dd {
  margin: 0;
  font-weight: 700;
}

.detail-panel span {
  display: block;
  color: rgba(238, 245, 255, 0.72);
  font-size: 11px;
  line-height: 1.5;
}

.flow-tooltip {
  position: absolute;
  z-index: 4;
  max-width: 240px;
  padding: 9px 10px;
  border: 1px solid rgba(218, 232, 255, 0.2);
  border-radius: 8px;
  color: #eef5ff;
  background: rgba(10, 16, 28, 0.9);
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.22);
  pointer-events: none;
}

.flow-tooltip strong,
.flow-tooltip span {
  display: block;
}

.flow-tooltip strong {
  margin-bottom: 4px;
  font-size: 12px;
}

.flow-tooltip span {
  color: rgba(238, 245, 255, 0.72);
  font-size: 11px;
  line-height: 1.45;
}

@keyframes flowMove {
  to {
    stroke-dashoffset: -26;
  }
}
</style>
