<template>
  <div class="sankey-card"> <!-- 最外层卡片容器，用来包住整个桑基图 -->
    <div class="sankey-header"><!-- 顶部区域，主要放图例或标题 -->
      <div class="sankey-legend"> <!-- 图例容器 -->
        <span
          v-for="item in legendItems"
          :key="item.label"
          class="legend-item"
        ><!-- 单个图例项开始 -->
          <i :style="{ background: item.color }"></i><!-- 图例前面的小圆点，颜色来自 item.color -->
          {{ item.label }}<!-- 显示图例文字，比如“时期”“身份”“行当” -->
        </span>
      </div>
    </div>

    <div ref="chartWrapRef" class="sankey-wrap">
      <svg ref="svgRef" class="sankey-svg"></svg>

      <div
        v-if="tooltip.show"
        class="sankey-tooltip"
        :style="{
          left: `${tooltip.x}px`,
          top: `${tooltip.y}px`,
        }"
      >
        <strong>{{ tooltip.title }}</strong>
        <span>{{ tooltip.desc }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as d3 from 'd3'
import {
  sankey,
  sankeyLinkHorizontal,
  sankeyJustify,
} from 'd3-sankey'

/**
 * =========================
 * 1. 可编辑总配置区
 * =========================
 * 后面你主要改这里就行。
 */
const chartConfig = {
  // 图表内边距
  margin: {
    top: 10,
    right: 20,
    bottom: 10,
    left: 2,
  },

  // 节点样式
  node: {
    width: 18,
    padding: 18,
    radius: 5,
    stroke: 'rgba(255,255,255,0.55)',
    strokeWidth: 1,
    opacity: 0.95,
    hoverOpacity: 1,// 鼠标悬浮相关节点时的透明度
  },

  // 连线样式
  link: {
    opacity: 0.28,
    hoverOpacity: 0.72,
    inactiveOpacity: 0.06,
    strokeLinecap: 'round',
    minWidth: 1,
  },

  // 文字样式
  label: {// 标签文字样式配置
    fontSize: 8,
    fontWeight: 700,
    color: '#000000',
    inactiveOpacity: 0.22, // 非相关标签弱化时的透明度
    offset: 10,// 标签距离节点的偏移距离
  },

  // 背景装饰
  background: {
    showColumnGuide: false,
  },

  // 动画
  transition: {
    duration: 1,
  },
}

/**
 * =========================
 * 2. 分层颜色配置区
 * =========================
 * 这里可以单独控制每个类别的颜色。
 */
const typeColorMap = {
  时期: '#b28a49',
  身份: '#c96b7d',
  行当: '#4d9bae',
}

const nodeColorMap = {
  '时期:明清': '#b07a3d',
  '时期:先秦': '#9b6a45',
  '时期:未识别': '#b8aa91',
  '时期:神话传说': '#8c6bb1',
  '时期:近现代': '#7c9f55',
  '时期:宋元': '#c58b39',
  '时期:秦汉': '#a6695b',
  '时期:三国': '#bf554f',
  '时期:隋唐': '#d09d4f',

  '身份:女性闺阁': '#d05f86',
  '身份:书生公子': '#5f94c8',
  '身份:帝王皇族': '#c4a64d',
  '身份:僧道仙怪': '#8e72bd',
  '身份:官员文臣': '#709c62',
  '身份:仆从差役': '#9c8065',
  '身份:将帅武人': '#c95b4a',
  '身份:市井滑稽': '#d28a35',

  '行当:旦': '#dc6d95',
  '行当:生': '#5594c5',
  '行当:丑': '#e29a3f',
  '行当:净': '#7564b3',
}

const legendItems = [
  { label: '时期', color: typeColorMap['时期'] },
  { label: '身份', color: typeColorMap['身份'] },
  { label: '行当', color: typeColorMap['行当'] },
]

/**
 * =========================
 * 3. 数据区
 * =========================
 * 你以后换数据，就主要改这里。
 */
const sankeyNodes = [
  { name: '时期:明清', depth: 0 },// 明清节点，depth 0 表示左侧第一列
  { name: '时期:先秦', depth: 0 },
  { name: '时期:未识别', depth: 0 },
  { name: '时期:神话传说', depth: 0 },
  { name: '时期:近现代', depth: 0 },
  { name: '时期:宋元', depth: 0 },
  { name: '时期:秦汉', depth: 0 },
  { name: '时期:三国', depth: 0 },
  { name: '时期:隋唐', depth: 0 },

  { name: '身份:女性闺阁', depth: 1 },
  { name: '身份:书生公子', depth: 1 },
  { name: '身份:帝王皇族', depth: 1 },
  { name: '身份:僧道仙怪', depth: 1 },
  { name: '身份:官员文臣', depth: 1 },
  { name: '身份:仆从差役', depth: 1 },
  { name: '身份:将帅武人', depth: 1 },
  { name: '身份:市井滑稽', depth: 1 },

  { name: '行当:旦', depth: 2 },
  { name: '行当:生', depth: 2 },
  { name: '行当:丑', depth: 2 },
  { name: '行当:净', depth: 2 },
]

const sankeyLinks = [
  { source: '时期:明清', target: '身份:女性闺阁', value: 22 },// 明清流向女性闺阁，数量 22
  { source: '时期:明清', target: '身份:帝王皇族', value: 8 },
  { source: '时期:明清', target: '身份:官员文臣', value: 9 },
  { source: '时期:先秦', target: '身份:帝王皇族', value: 14 },
  { source: '时期:先秦', target: '身份:将帅武人', value: 8 },
  { source: '时期:宋元', target: '身份:官员文臣', value: 10 },
  { source: '时期:宋元', target: '身份:市井滑稽', value: 5 },
  { source: '时期:秦汉', target: '身份:僧道仙怪', value: 7 },
  { source: '时期:三国', target: '身份:将帅武人', value: 18 },
  { source: '时期:三国', target: '身份:书生公子', value: 7 },
  { source: '时期:隋唐', target: '身份:将帅武人', value: 11 },
  { source: '时期:神话传说', target: '身份:僧道仙怪', value: 6 },
  { source: '时期:近现代', target: '身份:书生公子', value: 5 },
  { source: '时期:未识别', target: '身份:仆从差役', value: 3 },

  { source: '身份:女性闺阁', target: '行当:旦', value: 28 },
  { source: '身份:书生公子', target: '行当:生', value: 15 },
  { source: '身份:帝王皇族', target: '行当:生', value: 12 },
  { source: '身份:帝王皇族', target: '行当:净', value: 7 },
  { source: '身份:僧道仙怪', target: '行当:丑', value: 7 },
  { source: '身份:僧道仙怪', target: '行当:净', value: 5 },
  { source: '身份:官员文臣', target: '行当:生', value: 13 },
  { source: '身份:官员文臣', target: '行当:丑', value: 4 },
  { source: '身份:仆从差役', target: '行当:丑', value: 6 },
  { source: '身份:将帅武人', target: '行当:生', value: 17 },
  { source: '身份:将帅武人', target: '行当:净', value: 15 },
  { source: '身份:市井滑稽', target: '行当:丑', value: 8 },
]

const svgRef = ref(null)
const chartWrapRef = ref(null)
let resizeObserver = null

const tooltip = reactive({// tooltip 响应式状态对象
  show: false,
  x: 0,
  y: 0,
  title: '',
  desc: '',
})

const graphData = computed(() => ({// 计算属性，生成 D3 需要的数据副本
  nodes: sankeyNodes.map((item) => ({ ...item })),
  links: sankeyLinks.map((item) => ({ ...item })),
}))

function getNodeType(name) {// 根据节点名称获取类别
  return name.split(':')[0]// 用冒号分割，取前半部分，比如“时期:明清”得到“时期”
}

function getNodeShortName(name) {// 获取节点短名称
  return name.split(':')[1] || name// 用冒号分割，取后半部分，比如“时期:明清”得到“明清”
}

function getNodeColor(node) {// 获取节点颜色
  return nodeColorMap[node.name] || typeColorMap[getNodeType(node.name)] || '#999'// 优先用节点专属颜色，其次用类别颜色，最后用灰色兜底
}

function getLinkColor(link) {// 获取连线两端颜色
  const sourceColor = getNodeColor(link.source)// 获取 source 节点颜色
  const targetColor = getNodeColor(link.target)// 获取 target 节点颜色
  return { sourceColor, targetColor } // 返回起点和终点颜色
}

function drawSankey() {
  const wrapEl = chartWrapRef.value
  const svgEl = svgRef.value

  if (!wrapEl || !svgEl) return

  const width = wrapEl.clientWidth
  const height = wrapEl.clientHeight

  if (width <= 0 || height <= 0) return

  const {
    margin,
    node,
    link,
    label,
    background,
    transition,
  } = chartConfig

  const svg = d3.select(svgEl)

  svg.selectAll('*').remove()

  svg
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)

  const defs = svg.append('defs')

  /**
   * 背景纹理
   */
  const pattern = defs
    .append('pattern')
    .attr('id', 'sankey-dot-pattern')
    .attr('width', 18)
    .attr('height', 18)
    .attr('patternUnits', 'userSpaceOnUse')

  pattern
    .append('circle')
    .attr('cx', 2)
    .attr('cy', 2)
    .attr('r', 1)
    .attr('fill', 'rgba(80, 56, 36, 0.12)')

  svg
    .append('rect')
    .attr('width', width)
    .attr('height', height)
    .attr('fill', 'url(#sankey-dot-pattern)')
    .attr('opacity', 0.55)

  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom

  const sankeyLayout = sankey()
    .nodeId((d) => d.name)
    .nodeWidth(node.width)
    .nodePadding(node.padding)
    .nodeAlign(sankeyJustify)
    .extent([
      [margin.left, margin.top],
      [margin.left + innerWidth, margin.top + innerHeight],
    ])

  const graph = sankeyLayout(graphData.value)

  /**
   * 根据你写的 depth 手动修正 x 位置。
   * 这样你可以稳定控制三列：
   * depth 0 = 左
   * depth 1 = 中
   * depth 2 = 右
   */
  const depthCount = 3
  graph.nodes.forEach((d) => {
    const columnX = margin.left + (innerWidth / (depthCount - 1)) * d.depth
    d.x0 = columnX
    d.x1 = columnX + node.width
  })

  // 修正 x 位置后，重新计算 link 宽度和坐标
  sankeyLayout.update(graph)

  /**
   * 背景三列分区
   */
  if (background.showColumnGuide) {
    const columnTitles = [
      { title: '历史时期', depth: 0 },
      { title: '角色身份', depth: 1 },
      { title: '京剧行当', depth: 2 },
    ]

    const guideGroup = svg
      .append('g')
      .attr('class', 'column-guides')

    guideGroup
      .selectAll('rect')
      .data(columnTitles)
      .join('rect')
      .attr('x', (d) => margin.left + (innerWidth / 2) * d.depth - 42)
      .attr('y', margin.top - 18)
      .attr('width', 104)
      .attr('height', innerHeight + 36)
      .attr('rx', background.guideRadius)
      .attr('fill', background.guideColor)

    guideGroup
      .selectAll('text')
      .data(columnTitles)
      .join('text')
      .attr('x', (d) => margin.left + (innerWidth / 2) * d.depth + node.width / 2)
      .attr('y', margin.top - 6)
      .attr('text-anchor', 'middle')
      .attr('fill', 'rgba(70, 45, 28, 0.58)')
      .attr('font-size', 12)
      .attr('font-weight', 800)
      .text((d) => d.title)
  }

  /**
   * 连线渐变
   */
  graph.links.forEach((d, i) => {
    const { sourceColor, targetColor } = getLinkColor(d)

    const gradient = defs
      .append('linearGradient')
      .attr('id', `sankey-link-gradient-${i}`)
      .attr('gradientUnits', 'userSpaceOnUse')
      .attr('x1', d.source.x1)
      .attr('x2', d.target.x0)

    gradient
      .append('stop')
      .attr('offset', '0%')
      .attr('stop-color', sourceColor)

    gradient
      .append('stop')
      .attr('offset', '100%')
      .attr('stop-color', targetColor)
  })

  const mainGroup = svg
    .append('g')
    .attr('class', 'sankey-main')

  const linkGroup = mainGroup
    .append('g')
    .attr('class', 'sankey-links')
    .attr('fill', 'none')

  const nodeGroup = mainGroup
    .append('g')
    .attr('class', 'sankey-nodes')

  const labelGroup = mainGroup
    .append('g')
    .attr('class', 'sankey-labels')

  /**
   * 绘制连线
   */
  const linkSelection = linkGroup
    .selectAll('path')
    .data(graph.links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', sankeyLinkHorizontal())
    .attr('stroke', (d, i) => `url(#sankey-link-gradient-${i})`)
    .attr('stroke-width', (d) => Math.max(link.minWidth, d.width))
    .attr('stroke-linecap', link.strokeLinecap)
    .attr('opacity', 0)
    .on('mousemove', function (event, d) {
      showTooltip(event, {
        title: `${d.source.name} → ${d.target.name}`,
        desc: `角色数：${d.value}`,
      })

      highlightByLink(d, linkSelection, nodeSelection, textSelection)
    })
    .on('mouseleave', function () {
      hideTooltip()
      resetHighlight(linkSelection, nodeSelection, textSelection)
    })

  linkSelection
    .transition()
    .duration(transition.duration)
    .attr('opacity', link.opacity)

  /**
   * 绘制节点
   */
  const nodeSelection = nodeGroup
    .selectAll('rect')
    .data(graph.nodes)
    .join('rect')
    .attr('class', 'sankey-node')
    .attr('x', (d) => d.x0)
    .attr('y', (d) => d.y0)
    .attr('width', (d) => Math.max(1, d.x1 - d.x0))
    .attr('height', 0)
    .attr('rx', node.radius)
    .attr('fill', (d) => getNodeColor(d))
    .attr('stroke', node.stroke)
    .attr('stroke-width', node.strokeWidth)
    .attr('opacity', node.opacity)
    .style('filter', 'drop-shadow(0 6px 10px rgba(67, 45, 27, 0.18))')
    .on('mousemove', function (event, d) {
      showTooltip(event, {
        title: d.name,
        desc: `合计角色数：${d.value || 0}`,
      })

      highlightByNode(d, linkSelection, nodeSelection, textSelection)
    })
    .on('mouseleave', function () {
      hideTooltip()
      resetHighlight(linkSelection, nodeSelection, textSelection)
    })

  nodeSelection
    .transition()
    .duration(transition.duration)
    .attr('height', (d) => Math.max(2, d.y1 - d.y0))

  /**
   * 节点文字
   */
const textSelection = labelGroup
  .selectAll('.sankey-label')
  .data(graph.nodes)
  .join('text')
  .attr('class', 'sankey-label')
  .attr('x', (d) => (d.x0 + d.x1) / 2)
  .attr('y', (d) => {
    const text = getNodeShortName(d.name)
    const lineHeight = label.fontSize + 2
    const totalHeight = text.length * lineHeight
    return (d.y0 + d.y1) / 2 - totalHeight / 2 + lineHeight / 2
  })
  .attr('text-anchor', 'middle')
  .attr('dominant-baseline', 'middle')
  .attr('fill', '#000000')
  .attr('font-size', label.fontSize)
  .attr('font-weight', label.fontWeight)
  .attr('opacity', 0)
  .style('pointer-events', 'none')
  .each(function (d) {
    const text = getNodeShortName(d.name)
    const chars = text.split('')
    const lineHeight = label.fontSize + 2

    d3.select(this)
      .selectAll('tspan')
      .data(chars)
      .join('tspan')
      .attr('x', (d.x0 + d.x1) / 2)
      .attr('dy', (char, index) => {
        return index === 0 ? 0 : lineHeight
      })
      .text((char) => char)
  })

textSelection
  .transition()
  .duration(transition.duration)
  .attr('opacity', 1)

  /**
   * 节点数值小标签
   */
  labelGroup
    .selectAll('.sankey-value-label')
    .data(graph.nodes)
    .join('text')
    .attr('class', 'sankey-value-label')
    .attr('x', (d) => {
      if (d.depth === 0) return d.x0 - label.offset
      if (d.depth === 2) return d.x1 + label.offset
      return d.x0 + node.width / 2
    })
    .attr('y', (d) => (d.y0 + d.y1) / 2 + 16)
    .attr('text-anchor', (d) => {
      if (d.depth === 0) return 'end'
      if (d.depth === 2) return 'start'
      return 'middle'
    })
    .attr('fill', 'rgba(52, 43, 35, 0.48)')
    .attr('font-size', 10)
    .attr('font-weight', 600)
    .style('pointer-events', 'none')
    .text((d) => d.value ? `${d.value}` : '')
}

function showTooltip(event, content) {
  const wrapRect = chartWrapRef.value.getBoundingClientRect()

  tooltip.show = true
  tooltip.x = event.clientX - wrapRect.left + 14
  tooltip.y = event.clientY - wrapRect.top + 14
  tooltip.title = content.title
  tooltip.desc = content.desc
}

function hideTooltip() {
  tooltip.show = false
}

function highlightByNode(activeNode, linkSelection, nodeSelection, textSelection) {
  const relatedNodeNames = new Set()
  relatedNodeNames.add(activeNode.name)

  linkSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      const isRelated =
        d.source.name === activeNode.name ||
        d.target.name === activeNode.name

      if (isRelated) {
        relatedNodeNames.add(d.source.name)
        relatedNodeNames.add(d.target.name)
      }

      return isRelated ? chartConfig.link.hoverOpacity : chartConfig.link.inactiveOpacity
    })

  nodeSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      return relatedNodeNames.has(d.name)
        ? chartConfig.node.hoverOpacity
        : 0.18
    })

  textSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      return relatedNodeNames.has(d.name)
        ? 1
        : chartConfig.label.inactiveOpacity
    })
}

function highlightByLink(activeLink, linkSelection, nodeSelection, textSelection) {
  const relatedNodeNames = new Set([
    activeLink.source.name,
    activeLink.target.name,
  ])

  linkSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      const isSame =
        d.source.name === activeLink.source.name &&
        d.target.name === activeLink.target.name

      return isSame ? chartConfig.link.hoverOpacity : chartConfig.link.inactiveOpacity
    })

  nodeSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      return relatedNodeNames.has(d.name)
        ? chartConfig.node.hoverOpacity
        : 0.18
    })

  textSelection
    .transition()
    .duration(180)
    .attr('opacity', (d) => {
      return relatedNodeNames.has(d.name)
        ? 1
        : chartConfig.label.inactiveOpacity
    })
}

function resetHighlight(linkSelection, nodeSelection, textSelection) {
  linkSelection
    .transition()
    .duration(180)
    .attr('opacity', chartConfig.link.opacity)

  nodeSelection
    .transition()
    .duration(180)
    .attr('opacity', chartConfig.node.opacity)

  textSelection
    .transition()
    .duration(180)
    .attr('opacity', 1)
}

onMounted(async () => {
  await nextTick()
  drawSankey()

  resizeObserver = new ResizeObserver(() => {
    drawSankey()
  })

  if (chartWrapRef.value) {
    resizeObserver.observe(chartWrapRef.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<style scoped>
.sankey-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;/* 宽高包含 padding 和 border */
  position: relative;
  overflow: hidden; /* 超出卡片圆角的内容隐藏 */
}

.sankey-card::before {
  content: '';
  position: absolute;
  inset: 0px;/* 距离四边都是 10px */
  border: 1px solid rgba(119, 78, 42, 0.12);
  pointer-events: none;
}
.sankey-header {
  height: 20px;
}
/* background-color: black; */
.sankey-legend {
  display: flex;
  align-items: center;
  justify-content: space-between; /* 左右分布 */
  flex-wrap: wrap;
  padding: 2px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: rgba(48, 34, 23, 0.66);
  font-size: 12px;
  font-weight: 700;
}

.legend-item i {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.5);
}

.sankey-wrap {
  width: 100%;
  height: calc(100% - 58px);
  min-height: 340px;
  position: relative;
  z-index: 1;
}

.sankey-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.sankey-tooltip {
  position: absolute;
  z-index: 20;
  max-width: 260px;
  padding: 10px 12px;
  border-radius: 12px;
  pointer-events: none;

  background: rgba(42, 30, 21, 0.9);
  color: #fff8e8;
  box-shadow: 0 10px 28px rgba(42, 30, 21, 0.22);
  backdrop-filter: blur(8px);
}

.sankey-tooltip strong {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  line-height: 1.4;
}

.sankey-tooltip span {
  display: block;
  color: rgba(255, 248, 232, 0.76);
  font-size: 12px;
  line-height: 1.4;
}
</style>