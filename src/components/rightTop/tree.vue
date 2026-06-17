<template>
  <div ref="wrapRef" class="opera-tree-wrap">
    <svg ref="svgRef" class="opera-tree-svg"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as d3 from 'd3'

const wrapRef = ref(null)
const svgRef = ref(null)

let resizeObserver = null

const mockData = {
  name: '贾宝玉',
  relation: '核心人物',
  children: [
    {
      name: '林黛玉',
      relation: '知己 / 恋慕',
      children: [
        { name: '紫鹃', relation: '侍奉' },
        { name: '贾母', relation: '庇护' },
        { name: '王夫人', relation: '家族约束' }
      ]
    },
    {
      name: '薛宝钗',
      relation: '婚姻 / 礼法',
      children: [
        { name: '薛姨妈', relation: '母女' },
        { name: '薛蟠', relation: '兄妹' },
        { name: '袭人', relation: '日常照料' }
      ]
    },
    {
      name: '贾政',
      relation: '父权 / 规训',
      children: [
        { name: '王夫人', relation: '夫妻' },
        { name: '贾环', relation: '父子' },
        { name: '赵姨娘', relation: '妾室' }
      ]
    },
    {
      name: '王熙凤',
      relation: '管家 / 权力',
      children: [
        { name: '平儿', relation: '主仆' },
        { name: '贾琏', relation: '夫妻' },
        { name: '尤二姐', relation: '冲突' }
      ]
    }
  ]
}

// ==========================
// 尺寸参数：主要调这里
// ==========================

// 普通中层节点
const NODE_W = 30
const NODE_H = 62

// 根节点
const ROOT_NODE_W = 36
const ROOT_NODE_H = 68

// 底部叶子节点
const LEAF_NODE_W = 25
const LEAF_NODE_H = 60

// 节点之间距离
const NODE_GAP = 58
const LEVEL_GAP = 88

// 字体大小
const ROOT_FONT_SIZE = 14
const NODE_FONT_SIZE = 12
const LEAF_FONT_SIZE = 11
const RELATION_FONT_SIZE = 8

onMounted(() => {
  nextTick(() => {
    drawTree()

    resizeObserver = new ResizeObserver(() => {
      drawTree()
    })

    if (wrapRef.value) {
      resizeObserver.observe(wrapRef.value)
    }
  })
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

function drawTree() {
  const wrap = wrapRef.value
  const svgEl = svgRef.value
  if (!wrap || !svgEl) return

  const width = wrap.clientWidth || 900
  const height = wrap.clientHeight || 520

  const margin = {
    top: Math.min(42, height * 0.08),
    right: Math.min(34, width * 0.04),
    bottom: Math.min(34, height * 0.06),
    left: Math.min(34, width * 0.04)
  }

  const svg = d3.select(svgEl)
  svg.selectAll('*').remove()

  const root = d3.hierarchy(mockData)

  // ==========================
  // 树布局
  // ==========================
  const treeLayout = d3
    .tree()
    .nodeSize([NODE_GAP, LEVEL_GAP])
    .separation((a, b) => {
  // 最下面一层：同组也拉开，不同组更拉开
  if (a.depth === 2 && b.depth === 2) {
    return a.parent === b.parent ? 2 : 2.35
  }

  // 中间层
  if (a.depth === 1 && b.depth === 1) {
    return 1.35
  }

  return a.parent === b.parent ? 1.18 : 1.7
})

  treeLayout(root)

  let xMin = Infinity
  let xMax = -Infinity
  let maxNodeW = 0
  let maxNodeH = 0

  root.each(d => {
    const size = getNodeSize(d)
    maxNodeW = Math.max(maxNodeW, size.w)
    maxNodeH = Math.max(maxNodeH, size.h)

    if (d.x < xMin) xMin = d.x
    if (d.x > xMax) xMax = d.x
  })

  // 避免只有一个节点时 xMin 和 xMax 一样
  if (xMin === xMax) {
    xMin -= 1
    xMax += 1
  }

  const halfNodeW = maxNodeW / 2

  const xRangeMin = margin.left + halfNodeW
  const xRangeMax = width - margin.right - halfNodeW

  const yRangeMin = margin.top + ROOT_NODE_H / 2
  const yRangeMax = height - margin.bottom - LEAF_NODE_H / 2

  const xScale = d3
    .scaleLinear()
    .domain([xMin, xMax])
    .range([xRangeMin, Math.max(xRangeMin, xRangeMax)])

  const yScale = d3
    .scaleLinear()
    .domain([0, Math.max(1, root.height)])
    .range([yRangeMin, Math.max(yRangeMin, yRangeMax)])

  root.each(d => {
    d.x = xScale(d.x)
    d.y = yScale(d.depth)
  })

  svg
    .attr('width', '100%')
    .attr('height', '100%')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')

  // ==========================
  // SVG defs：纸质纹理、阴影、线条渐变
  // ==========================
  const defs = svg.append('defs')

  const paperFilter = defs
    .append('filter')
    .attr('id', 'paperRough')
    .attr('x', '-10%')
    .attr('y', '-10%')
    .attr('width', '120%')
    .attr('height', '120%')

  paperFilter
    .append('feTurbulence')
    .attr('type', 'fractalNoise')
    .attr('baseFrequency', 0.018)
    .attr('numOctaves', 2)
    .attr('result', 'noise')

  paperFilter
    .append('feDisplacementMap')
    .attr('in', 'SourceGraphic')
    .attr('in2', 'noise')
    .attr('scale', 0.55)

  const shadowFilter = defs
    .append('filter')
    .attr('id', 'softShadow')
    .attr('x', '-30%')
    .attr('y', '-30%')
    .attr('width', '160%')
    .attr('height', '160%')

  shadowFilter
    .append('feDropShadow')
    .attr('dx', 0)
    .attr('dy', 2)
    .attr('stdDeviation', 1.7)
    .attr('flood-color', '#8f7d57')
    .attr('flood-opacity', 0.2)

  const linkGradient = defs
  .append('linearGradient')
  .attr('id', 'linkGradient')
  .attr('gradientUnits', 'userSpaceOnUse')
  .attr('x1', 0)
  .attr('y1', 0)
  .attr('x2', width)
  .attr('y2', height)

  linkGradient
    .append('stop')
    .attr('offset', '0%')
    .attr('stop-color', '#b99b6b')

  linkGradient
    .append('stop')
    .attr('offset', '100%')
    .attr('stop-color', '#7d8b6a')

  // ==========================
  // 背景
  // ==========================
  svg
    .append('rect')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', width)
    .attr('height', height)
    .attr('fill', '#f3ead8')

  svg
    .append('path')
    .attr(
      'd',
      `
      M 0 ${height - 70}
      C ${width * 0.18} ${height - 105}, ${width * 0.34} ${height - 38}, ${width * 0.52} ${height - 82}
      C ${width * 0.7} ${height - 120}, ${width * 0.82} ${height - 44}, ${width} ${height - 92}
      L ${width} ${height}
      L 0 ${height}
      Z
    `
    )
    .attr('fill', '#d9caa8')
    .attr('opacity', 0.2)

  const g = svg
    .append('g')
    .attr('transform', 'translate(0, 0)')

  // ==========================
  // 连线
  // ==========================
  const links = root.links()

  const linkGroup = g
    .append('g')
    .attr('class', 'link-group')

  linkGroup
  .selectAll('path')
  .data(links)
  .join('path')
  .attr('class', 'tree-link')
  .attr('d', d => createLinkPath(d))
  .attr('fill', 'none')
  .attr('stroke', 'url(#linkGradient)')
  .attr('stroke-width', 1.15)
  .attr('stroke-opacity', 0.62)
  .attr('stroke-linecap', 'round')

  // ==========================
  // 关系文字
  // ==========================
  const labelGroup = g
    .append('g')
    .attr('class', 'relation-label-group')

  const labels = labelGroup
  .selectAll('g')
  .data(links)
  .join('g')
  .attr('class', 'relation-label')
  .attr('transform', d => {
    const pos = getRelationLabelAboveNode(d)
    return `translate(${pos.x}, ${pos.y})`
  })
// ==========================
// 关系标签：放到目标节点上方
// ==========================
function getRelationLabelAboveNode(d) {
  const targetSize = getNodeSize(d.target)

  const x = d.target.x

  // 标签距离节点顶部的距离
  // depth 1 是中间层，可以稍微高一点
  // depth 2 是底层，稍微近一点
  const labelGap = d.target.depth === 1 ? 18 : 14

  const y = d.target.y - targetSize.h / 2 - labelGap

  return { x, y }
}
  labels
  .append('rect')
  .attr('x', d => -getTextWidth(d.target.data.relation || '') / 2 - 5)
  .attr('y', -7)
  .attr('width', d => getTextWidth(d.target.data.relation || '') + 10)
  .attr('height', 14)
  .attr('rx', 7)
  .attr('ry', 7)
  .attr('fill', '#f3ead8')
  .attr('fill-opacity', 0.55)
  .attr('stroke', '#c4b182')
  .attr('stroke-width', 0.45)
  .attr('stroke-opacity', 0.65)

  labels
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.34em')
    .attr('font-size', RELATION_FONT_SIZE)
    .attr('font-family', 'KaiTi, STKaiti, FangSong, serif')
    .attr('fill', '#6f6044')
    .text(d => d.target.data.relation || '')

  // ==========================
  // 节点
  // ==========================
  const nodeGroup = g
    .append('g')
    .attr('class', 'node-group')

  const nodes = nodeGroup
    .selectAll('g')
    .data(root.descendants())
    .join('g')
    .attr('class', 'tree-node')
    .attr('transform', d => `translate(${d.x}, ${d.y})`)
    .style('cursor', 'pointer')

  nodes.each(function (d) {
    const node = d3.select(this)

    const size = getNodeSize(d)
    const nodeW = size.w
    const nodeH = size.h

    // 主体竖向人物牌
    node
      .append('rect')
      .attr('class', 'node-main-rect')
      .attr('x', -nodeW / 2)
      .attr('y', -nodeH / 2)
      .attr('width', nodeW)
      .attr('height', nodeH)
      .attr('rx', nodeW / 2)
      .attr('ry', nodeW / 2)
      .attr('fill', getNodeFill(d))
      .attr('stroke', '#b8a77b')
      .attr('stroke-width', d.depth === 0 ? 1.5 : 1.15)
      .attr('filter', 'url(#softShadow)')

    // 外层手绘边框
    node
      .append('path')
      .attr('class', 'node-rough-border')
      .attr(
        'd',
        roundedRectPath(
          -nodeW / 2 + 2,
          -nodeH / 2 + 2,
          nodeW - 4,
          nodeH - 4,
          nodeW / 2 - 2
        )
      )
      .attr('fill', 'none')
      .attr('stroke', '#b7a77a')
      .attr('stroke-width', 0.95)
      .attr('stroke-opacity', 0.88)
      .attr('filter', 'url(#paperRough)')

    // 人物名：竖排
    const nameChars = Array.from(d.data.name || '')
const fontSize = size.fontSize

// 字与字之间的距离，想紧一点就 fontSize - 1，想松一点就 fontSize + 1
const lineGap = fontSize

// 用这个公式，比 startY 那种更稳
const textOffsetY = 0

const text = node
  .append('text')
  .attr('class', 'node-name')
  .attr('text-anchor', 'middle')
  .attr('dominant-baseline', 'middle')
  .attr('alignment-baseline', 'middle')
  .attr('font-size', fontSize)
  .attr('font-weight', d.depth === 0 ? 700 : 600)
  .attr('font-family', 'KaiTi, STKaiti, FangSong, serif')
  .attr('fill', '#3c3021')

text
  .selectAll('tspan')
  .data(nameChars)
  .join('tspan')
  .attr('x', 0)
  .attr('y', (char, i) => {
    return (i - (nameChars.length - 1) / 2) * lineGap + textOffsetY
  })
  .attr('dominant-baseline', 'middle')
  .attr('alignment-baseline', 'middle')
  .text(char => char)
  })

  // ==========================
  // 悬停交互
  // ==========================
  nodes
    .on('mouseenter', function (event, d) {
      const related = new Set()
      related.add(d)

      if (d.parent) {
        related.add(d.parent)
      }

      if (d.children) {
        d.children.forEach(child => related.add(child))
      }

      nodes
        .transition()
        .duration(160)
        .style('opacity', n => related.has(n) ? 1 : 0.26)

      linkGroup
        .selectAll('path')
        .transition()
        .duration(160)
        .attr('stroke-opacity', l => {
          return l.source === d || l.target === d ? 0.92 : 0.14
        })
        .attr('stroke-width', l => {
          return l.source === d || l.target === d ? 2 : 0.8
        })

      labels
        .transition()
        .duration(160)
        .style('opacity', l => {
          return l.source === d || l.target === d ? 1 : 0.22
        })
    })
    .on('mouseleave', function () {
      nodes
        .transition()
        .duration(160)
        .style('opacity', 1)

      linkGroup
        .selectAll('path')
        .transition()
        .duration(160)
        .attr('stroke-opacity', 0.5)
        .attr('stroke-width', 1)

      labels
        .transition()
        .duration(160)
        .style('opacity', 1)
    })
}

// ==========================
// 根据层级返回节点尺寸
// ==========================
function getNodeSize(d) {
  if (d.depth === 0) {
    return {
      w: ROOT_NODE_W,
      h: ROOT_NODE_H,
      fontSize: ROOT_FONT_SIZE
    }
  }

  if (!d.children || d.children.length === 0) {
    return {
      w: LEAF_NODE_W,
      h: LEAF_NODE_H,
      fontSize: LEAF_FONT_SIZE
    }
  }

  return {
    w: NODE_W,
    h: NODE_H,
    fontSize: NODE_FONT_SIZE
  }
}

// ==========================
// 不同层级稍微区分颜色
// ==========================
function getNodeFill(d) {
  if (d.depth === 0) return '#dfcfaa'
  if (d.depth === 1) return '#e6d8b9'
  return '#eadfc8'
}

// ==========================
// 连线：树状弯曲线
// ==========================
function createLinkPath(d) {
  const sourceSize = getNodeSize(d.source)
  const targetSize = getNodeSize(d.target)

  const sourceX = d.source.x
  const sourceY = d.source.y + sourceSize.h / 2 - 2

  const targetX = d.target.x
  const targetY = d.target.y - targetSize.h / 2 + 2

  const midY = (sourceY + targetY) / 2

  return `
    M ${sourceX},${sourceY}
    C ${sourceX},${midY}
      ${targetX},${midY}
      ${targetX},${targetY}
  `
}

// ==========================
// 关系标签文字宽度
// ==========================
function getTextWidth(text) {
  return String(text || '').length * 9
}

// ==========================
// 普通圆角矩形路径
// ==========================
function roundedRectPath(x, y, w, h, r) {
  return `
    M ${x + r},${y}
    H ${x + w - r}
    Q ${x + w},${y} ${x + w},${y + r}
    V ${y + h - r}
    Q ${x + w},${y + h} ${x + w - r},${y + h}
    H ${x + r}
    Q ${x},${y + h} ${x},${y + h - r}
    V ${y + r}
    Q ${x},${y} ${x + r},${y}
    Z
  `
}
</script>

<style scoped>
.opera-tree-wrap {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 18px;
  background:
    radial-gradient(circle at 20% 10%, rgba(255, 248, 228, 0.95), rgba(239, 226, 196, 0.95)),
    linear-gradient(180deg, #f3ead8 0%, #eadcc0 100%);
}

.opera-tree-svg {
  display: block;
  width: 100%;
  height: 100%;
}

.tree-link {
  pointer-events: none;
}

.relation-label {
  pointer-events: none;
}

.tree-node text {
  user-select: none;
}
</style>
