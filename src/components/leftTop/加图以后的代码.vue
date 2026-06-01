<template>
  <div class="sankey-card">
    <div class="sankey-header">
      <div class="sankey-legend">
        <span
          v-for="item in legendItems"
          :key="item.label"
          class="legend-item"
        >
          <i :style="{ background: item.color }"></i>
          {{ item.label }}
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
  sankeyJustify,
} from 'd3-sankey'
import sheng from "../../assets/step1/生.png"
import dan from "../../assets/step1/旦.png"
import jing from "../../assets/step1/净.png"
import chou from "../../assets/step1/丑.png"
const chartConfig = {
  margin: {
    top: 10,
    right: 42,
    bottom: 10,
    left: 8,
  },

  node: {
    width: 18,
    middleBarWidth: 7,
    padding: 18,
    radius: 5,
    stroke: 'rgba(255,255,255,0.55)',
    strokeWidth: 1,
    opacity: 0.95,
    hoverOpacity: 1,
  },

  circle: {
    radius: 25,

    // 第三列圆圈虚线边框向圆心收缩多少
    // 越大，虚线边框越靠里面
    borderInset: 2,

    stroke: 'rgba(194, 176, 143, 1)',
    strokeWidth: 1.5,
    strokeDasharray: '2 1',
  },

  link: {
    opacity: 0.28,
    hoverOpacity: 0.72,
    inactiveOpacity: 0.06,
    strokeLinecap: 'round',
    minWidth: 1,
  },

  label: {
    fontSize: 8,
    fontWeight: 700,
    color: '#000000',
    inactiveOpacity: 0.22,
    offset: 10,
  },

  background: {
    showColumnGuide: false,
  },

  transition: {
    duration: 500,
  },
}

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

const sankeyNodes = [
  { name: '时期:明清', depth: 0 },
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
  { source: '时期:明清', target: '身份:女性闺阁', value: 22 },
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

const tooltip = reactive({
  show: false,
  x: 0,
  y: 0,
  title: '',
  desc: '',
})

const graphData = computed(() => ({
  nodes: sankeyNodes.map((item) => ({ ...item })),
  links: sankeyLinks.map((item) => ({ ...item })),
}))

function getNodeType(name) {
  return name.split(':')[0]
}

function getNodeShortName(name) {
  return name.split(':')[1] || name
}

function getNodeColor(node) {
  return nodeColorMap[node.name] || typeColorMap[getNodeType(node.name)] || '#999'
}

function getLinkColor(link) {
  const sourceColor = getNodeColor(link.source)
  const targetColor = getNodeColor(link.target)

  return {
    sourceColor,
    targetColor,
  }
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

  const depthCount = 3

  graph.nodes.forEach((d) => {
    const columnX = margin.left + (innerWidth / (depthCount - 1)) * d.depth

    if (d.depth === 1) {
      d.x0 = columnX
      d.x1 = columnX + node.middleBarWidth
    } else if (d.depth === 2) {
      d.x0 = columnX - chartConfig.circle.radius
      d.x1 = columnX + chartConfig.circle.radius
    } else {
      d.x0 = columnX
      d.x1 = columnX + node.width
    }
  })

  // 重点：只改每列内部的 y 位置，不动 x 位置
  // 每一列内部的节点会按照相同间隔排列
  const columns = d3.group(graph.nodes, (d) => d.depth)

  columns.forEach((columnNodes) => {
    columnNodes.sort((a, b) => a.y0 - b.y0)

    const visualHeights = columnNodes.map((d) => {
      if (d.depth === 2) {
        return chartConfig.circle.radius * 2
      }

      return Math.max(2, d.y1 - d.y0)
    })

    const totalVisualHeight = d3.sum(visualHeights)

    const gap =
      columnNodes.length > 1
        ? Math.max(6, (innerHeight - totalVisualHeight) / (columnNodes.length - 1))
        : 0

    let currentY = margin.top

    columnNodes.forEach((d, index) => {
      const visualHeight = visualHeights[index]

      if (d.depth === 2) {
        const centerY = currentY + visualHeight / 2

        d.y0 = centerY - chartConfig.circle.radius
        d.y1 = centerY + chartConfig.circle.radius
      } else {
        d.y0 = currentY
        d.y1 = currentY + visualHeight
      }

      currentY += visualHeight + gap
    })
  })

  sankeyLayout.update(graph)

  function getNodeCenterY(d) {
    return (d.y0 + d.y1) / 2
  }

  function getNodeCenterX(d) {
    return (d.x0 + d.x1) / 2
  }

  function getCustomLinkPath(d) {
    const sourceX = d.source.depth === 2
      ? getNodeCenterX(d.source) + chartConfig.circle.radius
      : d.source.x1

    const sourceY = d.source.depth === 2
      ? getNodeCenterY(d.source)
      : d.y0

    const targetX = d.target.depth === 2
      ? getNodeCenterX(d.target) - chartConfig.circle.radius
      : d.target.x0

    const targetY = d.target.depth === 2
      ? getNodeCenterY(d.target)
      : d.y1

    const midX = (sourceX + targetX) / 2

    return `
      M ${sourceX},${sourceY}
      C ${midX},${sourceY}
        ${midX},${targetY}
        ${targetX},${targetY}
    `
  }

  function fitGroupInsideSvg(group, svgWidth, svgHeight) {
    const groupNode = group.node()

    if (!groupNode) return

    const bbox = groupNode.getBBox()

    if (!bbox.width || !bbox.height) return

    const safePadding = 2

    const scaleX = (svgWidth - safePadding * 2) / bbox.width
    const scaleY = (svgHeight - safePadding * 2) / bbox.height

    const scale = Math.min(1, scaleX, scaleY)

    const scaledWidth = bbox.width * scale
    const scaledHeight = bbox.height * scale

    const translateX = (svgWidth - scaledWidth) / 2 - bbox.x * scale
    const translateY = (svgHeight - scaledHeight) / 2 - bbox.y * scale

    group.attr(
      'transform',
      `translate(${translateX}, ${translateY}) scale(${scale})`
    )
  }

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
      .attr('rx', 14)
      .attr('fill', 'rgba(89, 61, 38, 0.06)')

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

  graph.links.forEach((d, i) => {
    const { sourceColor, targetColor } = getLinkColor(d)

    const gradientX1 = d.source.depth === 2
      ? getNodeCenterX(d.source) + chartConfig.circle.radius
      : d.source.x1

    const gradientX2 = d.target.depth === 2
      ? getNodeCenterX(d.target) - chartConfig.circle.radius
      : d.target.x0

    const gradient = defs
      .append('linearGradient')
      .attr('id', `sankey-link-gradient-${i}`)
      .attr('gradientUnits', 'userSpaceOnUse')
      .attr('x1', gradientX1)
      .attr('x2', gradientX2)

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

  const linkSelection = linkGroup
    .selectAll('path')
    .data(graph.links)
    .join('path')
    .attr('class', 'sankey-link')
    .attr('d', getCustomLinkPath)
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

  const nodeSelection = nodeGroup
    .selectAll('.sankey-node-shape')
    .data(graph.nodes)
    .join((enter) =>
      enter.append(function (d) {
        return document.createElementNS(
          'http://www.w3.org/2000/svg',
          d.depth === 2 ? 'circle' : 'rect'
        )
      })
    )
    .attr('class', 'sankey-node-shape')
    .attr('fill', (d) => getNodeColor(d))
    .attr('stroke', (d) => {
      return d.depth === 2 ? 'none' : node.stroke
    })
    .attr('stroke-width', (d) => {
      return d.depth === 2 ? 0 : node.strokeWidth
    })
    .attr('stroke-dasharray', 'none')
    .attr('opacity', node.opacity)
    .style('filter', (d) => {
      if (d.depth === 2) {
        return 'drop-shadow(0 4px 10px rgba(67, 45, 27, 0.22))'
      }

      return 'drop-shadow(0 6px 10px rgba(67, 45, 27, 0.18))'
    })
    .each(function (d) {
      const shape = d3.select(this)

      if (d.depth === 2) {
        shape
          .attr('cx', getNodeCenterX(d))
          .attr('cy', getNodeCenterY(d))
          .attr('r', 0)
      } else {
        shape
          .attr('x', d.x0)
          .attr('y', d.y0)
          .attr('width', Math.max(1, d.x1 - d.x0))
          .attr('height', 0)
          .attr('rx', node.radius)
      }
    })
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
    .each(function (d) {
      const shape = d3.select(this)

      if (d.depth === 2) {
        shape.attr('r', chartConfig.circle.radius)
      } else {
        shape.attr('height', Math.max(2, d.y1 - d.y0))
      }
    })

  // 第三列圆圈的内缩虚线边框
  // 注意：这个边框只是往圆心靠，圆圈本身和第三列位置都不会乱动
  nodeGroup
    .selectAll('.sankey-circle-inner-border')
    .data(graph.nodes.filter((d) => d.depth === 2))
    .join('circle')
    .attr('class', 'sankey-circle-inner-border')
    .attr('cx', (d) => getNodeCenterX(d))
    .attr('cy', (d) => getNodeCenterY(d))
    .attr('r', chartConfig.circle.radius - chartConfig.circle.borderInset)
    .attr('fill', 'none')
    .attr('stroke', chartConfig.circle.stroke)
    .attr('stroke-width', chartConfig.circle.strokeWidth)
    .attr('stroke-dasharray', chartConfig.circle.strokeDasharray)
    .attr('opacity', 0.95)
    .style('pointer-events', 'none')

  const textSelection = labelGroup
    .selectAll('.sankey-label')
    .data(graph.nodes.filter((d) => d.depth !== 1))
    .join('text')
    .attr('class', 'sankey-label')
    .attr('x', (d) => getNodeCenterX(d))
    .attr('y', (d) => {
      if (d.depth === 2) {
        return getNodeCenterY(d)
      }

      const text = getNodeShortName(d.name)
      const lineHeight = label.fontSize + 2
      const totalHeight = text.length * lineHeight

      return getNodeCenterY(d) - totalHeight / 2 + lineHeight / 2
    })
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('fill', (d) => {
      return d.depth === 2 ? '#fff8e8' : '#000000'
    })
    .attr('font-size', (d) => {
      return d.depth === 2 ? 10 : label.fontSize
    })
    .attr('font-weight', label.fontWeight)
    .attr('opacity', 0)
    .style('pointer-events', 'none')
    .each(function (d) {
      const currentText = d3.select(this)

      currentText.selectAll('*').remove()

      if (d.depth === 2) {
        currentText.text(getNodeShortName(d.name))
      } else {
        const text = getNodeShortName(d.name)
        const chars = text.split('')
        const lineHeight = label.fontSize + 2

        currentText
          .selectAll('tspan')
          .data(chars)
          .join('tspan')
          .attr('x', getNodeCenterX(d))
          .attr('dy', (char, index) => {
            return index === 0 ? 0 : lineHeight
          })
          .text((char) => char)
      }
    })

  textSelection
    .transition()
    .duration(transition.duration)
    .attr('opacity', 1)

  requestAnimationFrame(() => {
    fitGroupInsideSvg(mainGroup, width, height)
  })
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
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
}

.sankey-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border: 1px solid rgba(119, 78, 42, 0.12);
  pointer-events: none;
}

.sankey-header {
  height: 20px;
}

.sankey-legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
  height: calc(100% - 20px);
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