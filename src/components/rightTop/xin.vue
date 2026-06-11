<template>
  <div class="chart-one">
    <select v-model="selectedScriptKey" class="script-select">
      <option
        v-for="script in scriptOptions"
        :key="script.key"
        :value="script.key"
      >
        {{ script.title }}
      </option>
    </select>

    <div ref="chartRef" class="chart-box">
      <svg ref="svgRef"></svg>

      <div
        v-if="tooltip.show"
        class="tooltip"
        :style="{
          left: tooltip.x + 'px',
          top: tooltip.y + 'px',
        }"
      >
        <div>{{ tooltip.source }} → {{ tooltip.target }}</div>
        <div>关系类型：{{ tooltip.relationType }}</div>
        <div>权重：{{ tooltip.weight }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as d3 from 'd3'
import * as XLSX from 'xlsx'

const chartRef = ref(null)
const svgRef = ref(null)

const rawData = ref([])
const selectedScriptKey = ref('')

const tooltip = reactive({
  show: false,
  x: 0,
  y: 0,
  source: '',
  target: '',
  relationType: '',
  weight: 0,
})

let resizeObserver = null

const DATA_URL = '/数据表合集/2/p2_edges.xlsx'

// 主色
const GOLD = '#B98A45'
const LIGHT_GOLD = '#E8D1A5'
const DEEP_RED = '#B84A36'
const GREEN = '#5F8B7A'
const INK = '#4A2B1A'

// 节点大小
// 想让圆牌更大，改大 NODE_R
// 想让圆牌更小，改小 NODE_R
const NODE_R = 28

// 读取 Excel 数据
async function loadData() {
  try {
    const res = await fetch(encodeURI(DATA_URL))

    if (!res.ok) {
      throw new Error(`数据读取失败：${res.status}`)
    }

    const buffer = await res.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' })

    rawData.value = rows
      .map((row) => ({
        script_id: String(row.script_id || '').trim(),
        script_title: String(row.script_title || '').trim(),
        source: String(row.source || '').trim(),
        target: String(row.target || '').trim(),
        weight: Number(row.weight || 0),
        relation_type: String(row.relation_type || '').trim(),
      }))
      .filter((row) => {
        return (
          row.script_id &&
          row.script_title &&
          row.source &&
          row.target &&
          row.weight > 0
        )
      })

    if (scriptOptions.value.length > 0) {
      selectedScriptKey.value = scriptOptions.value[0].key
    }
  } catch (error) {
    console.error(error)
    rawData.value = []
  }
}

// 剧本下拉框选项
const scriptOptions = computed(() => {
  const map = new Map()

  rawData.value.forEach((item) => {
    const key = `${item.script_id}__${item.script_title}`

    if (!map.has(key)) {
      map.set(key, {
        key,
        id: item.script_id,
        title: item.script_title,
      })
    }
  })

  return Array.from(map.values())
})

// 当前剧本的边数据
const currentEdges = computed(() => {
  if (!selectedScriptKey.value) return []

  const [scriptId, scriptTitle] = selectedScriptKey.value.split('__')

  return rawData.value.filter((item) => {
    return item.script_id === scriptId && item.script_title === scriptTitle
  })
})

// 根据关系类型返回线颜色
function getRelationColor(type) {
  if (type.includes('师承')) return DEEP_RED
  if (type.includes('合作')) return '#D9A65F'
  if (type.includes('同台')) return GREEN
  if (type.includes('影响')) return '#C8A66A'

  return '#D9A65F'
}

// 画小红花
function drawFlower(group, y) {
  const flower = group.append('g').attr('class', 'node-flower').attr('transform', `translate(0, ${y})`)

  const petals = [
    { x: 0, y: -3 },
    { x: 3, y: 0 },
    { x: 0, y: 3 },
    { x: -3, y: 0 },
  ]

  flower
    .selectAll('ellipse')
    .data(petals)
    .join('ellipse')
    .attr('cx', (d) => d.x)
    .attr('cy', (d) => d.y)
    .attr('rx', 2.4)
    .attr('ry', 3.4)
    .attr('fill', '#C74432')
    .attr('stroke', '#8F2A20')
    .attr('stroke-width', 0.5)

  flower
    .append('circle')
    .attr('r', 1.7)
    .attr('fill', '#F1D47A')
    .attr('stroke', '#8F2A20')
    .attr('stroke-width', 0.5)
}

// 画底部小装饰
function drawBottomOrnament(group, y) {
  const deco = group.append('g').attr('class', 'node-bottom-deco').attr('transform', `translate(0, ${y})`)

  deco
    .append('path')
    .attr('d', 'M -10 0 C -6 5, -2 5, 0 0 C 2 5, 6 5, 10 0')
    .attr('fill', 'none')
    .attr('stroke', GOLD)
    .attr('stroke-width', 1.1)
    .attr('stroke-linecap', 'round')

  deco
    .append('circle')
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('r', 2)
    .attr('fill', '#C74432')
    .attr('stroke', '#8F2A20')
    .attr('stroke-width', 0.5)
}

// 画京剧圆牌节点
function drawOperaNode(nodeGroup) {
  // 外层淡金阴影
  nodeGroup
    .append('circle')
    .attr('r', NODE_R + 5)
    .attr('fill', '#F4E6C9')
    .attr('opacity', 0.5)

  // 外圈金边
  nodeGroup
    .append('circle')
    .attr('r', NODE_R + 2)
    .attr('fill', '#FFF8E9')
    .attr('stroke', GOLD)
    .attr('stroke-width', 1.8)

  // 第二层细边
  nodeGroup
    .append('circle')
    .attr('r', NODE_R - 2)
    .attr('fill', '#FFF9EE')
    .attr('stroke', LIGHT_GOLD)
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', '3 2')

  // 中心浅色底
  nodeGroup
    .append('circle')
    .attr('r', NODE_R - 7)
    .attr('fill', '#FFFDF5')
    .attr('stroke', '#E6D1A4')
    .attr('stroke-width', 0.8)

  // 左右小金点
  nodeGroup
    .append('circle')
    .attr('cx', -NODE_R - 2)
    .attr('cy', 0)
    .attr('r', 2)
    .attr('fill', GOLD)

  nodeGroup
    .append('circle')
    .attr('cx', NODE_R + 2)
    .attr('cy', 0)
    .attr('r', 2)
    .attr('fill', GOLD)

  // 顶部红花
  drawFlower(nodeGroup, -NODE_R - 5)

  // 底部纹饰
  drawBottomOrnament(nodeGroup, NODE_R - 2)
}

// 绘图
function drawChart() {
  const container = chartRef.value
  const svgEl = svgRef.value

  if (!container || !svgEl) return

  const width = container.clientWidth
  const height = container.clientHeight

  const svg = d3.select(svgEl)

  svg.selectAll('*').remove()

  svg.attr('width', width).attr('height', height)

  const edges = currentEdges.value

  if (!edges.length || width <= 0 || height <= 0) return

  const margin = {
    top: NODE_R + 34,
    right: NODE_R + 42,
    bottom: NODE_R + 34,
    left: NODE_R + 42,
  }

  // 定义渐变和阴影
  const defs = svg.append('defs')

  const glow = defs
    .append('filter')
    .attr('id', 'nodeGlow')
    .attr('x', '-40%')
    .attr('y', '-40%')
    .attr('width', '180%')
    .attr('height', '180%')

  glow
    .append('feDropShadow')
    .attr('dx', 0)
    .attr('dy', 2)
    .attr('stdDeviation', 2)
    .attr('flood-color', '#9A6B32')
    .attr('flood-opacity', 0.28)

  // 获取所有角色节点
  const roleSet = new Set()

  edges.forEach((edge) => {
    roleSet.add(edge.source)
    roleSet.add(edge.target)
  })

  const roles = Array.from(roleSet)

  // 圆心位置
  const centerX = width / 2
  const centerY = height / 2 + 4

  // 圆半径
  // 想让整体圆更大，改 0.46 / 0.48
  // 想让整体圆更小，改 0.38 / 0.4
  const radius = Math.min(
    width - margin.left - margin.right,
    height - margin.top - margin.bottom,
  ) * 0.55

  // 计算角色关系数量
  const degreeMap = new Map()

  roles.forEach((role) => {
    degreeMap.set(role, 0)
  })

  edges.forEach((edge) => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1)
    degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1)
  })

  const sortedRoles = [...roles].sort((a, b) => {
    return (degreeMap.get(b) || 0) - (degreeMap.get(a) || 0)
  })

  // 穿插排序，避免重要节点全部挤在一侧
  const orderedRoles = []

  sortedRoles.forEach((role, index) => {
    if (index % 2 === 0) {
      orderedRoles.push(role)
    } else {
      orderedRoles.unshift(role)
    }
  })

  // 计算每个节点的圆周位置
  const nodePositionMap = new Map()

  orderedRoles.forEach((role, index) => {
    const angle = (Math.PI * 2 * index) / orderedRoles.length - Math.PI / 2

    const x = centerX + Math.cos(angle) * radius
    const y = centerY + Math.sin(angle) * radius

    nodePositionMap.set(role, {
      x,
      y,
      angle,
    })
  })

  const maxWeight = d3.max(edges, (d) => d.weight) || 1
  const minWeight = d3.min(edges, (d) => d.weight) || 1

  // 线宽表示权重
  const lineWidthScale = d3
    .scaleLinear()
    .domain([minWeight, maxWeight])
    .range([0.8, 5.6])

  // 线透明度
  const opacityScale = d3
    .scaleLinear()
    .domain([minWeight, maxWeight])
    .range([0.18, 0.72])

  // 弧线弯曲程度
  const CURVE_RATIO = 0.56

  // 生成圆内关系线
  function getArcPath(edge, index) {
    const sourcePos = nodePositionMap.get(edge.source)
    const targetPos = nodePositionMap.get(edge.target)

    if (!sourcePos || !targetPos) return ''

    const x1 = sourcePos.x
    const y1 = sourcePos.y
    const x2 = targetPos.x
    const y2 = targetPos.y

    const midX = (x1 + x2) / 2
    const midY = (y1 + y2) / 2

    const controlX = midX + (centerX - midX) * CURVE_RATIO
    const controlY = midY + (centerY - midY) * CURVE_RATIO

    // 让重叠线稍微散开
    const offset = ((index % 7) - 3) * 3

    return `
      M ${x1},${y1}
      Q ${controlX + offset},${controlY - offset}
        ${x2},${y2}
    `
  }

  // 外层装饰圆环
  svg
    .append('circle')
    .attr('cx', centerX)
    .attr('cy', centerY)
    .attr('r', radius + NODE_R + 14)
    .attr('fill', 'none')
    .attr('stroke', '#D6AA68')
    .attr('stroke-width', 1.2)
    .attr('opacity', 0.72)

  svg
    .append('circle')
    .attr('cx', centerX)
    .attr('cy', centerY)
    .attr('r', radius + NODE_R + 7)
    .attr('fill', 'none')
    .attr('stroke', '#E3C58E')
    .attr('stroke-width', 0.9)
    .attr('opacity', 0.6)

  svg
    .append('circle')
    .attr('cx', centerX)
    .attr('cy', centerY)
    .attr('r', radius)
    .attr('fill', 'none')
    .attr('stroke', '#C75C43')
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', '3 9')
    .attr('stroke-linecap', 'round')
    .attr('opacity', 0.75)

  // 画关系线
  svg
    .append('g')
    .attr('class', 'arc-group')
    .selectAll('path')
    .data(edges)
    .join('path')
    .attr('d', (d, i) => getArcPath(d, i))
    .attr('fill', 'none')
    .attr('stroke', (d) => getRelationColor(d.relation_type))
    .attr('stroke-width', (d) => lineWidthScale(d.weight))
    .attr('opacity', (d) => opacityScale(d.weight))
    .attr('cursor', 'pointer')
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .on('mouseenter', function (event, d) {
      d3.select(this)
        .attr('opacity', 0.95)
        .attr('stroke-width', lineWidthScale(d.weight) + 1.6)

      tooltip.show = true
      tooltip.source = d.source
      tooltip.target = d.target
      tooltip.relationType = d.relation_type || '无'
      tooltip.weight = d.weight
    })
    .on('mousemove', function (event) {
      const rect = container.getBoundingClientRect()

      tooltip.x = event.clientX - rect.left + 12
      tooltip.y = event.clientY - rect.top + 12
    })
    .on('mouseleave', function (event, d) {
      d3.select(this)
        .attr('opacity', opacityScale(d.weight))
        .attr('stroke-width', lineWidthScale(d.weight))

      tooltip.show = false
    })

  // 画节点
  const nodeGroup = svg
    .append('g')
    .attr('class', 'node-group')
    .selectAll('g')
    .data(orderedRoles)
    .join('g')
    .attr('class', 'opera-node')
    .attr('transform', (d) => {
      const pos = nodePositionMap.get(d)
      return `translate(${pos.x}, ${pos.y})`
    })
    .style('filter', 'url(#nodeGlow)')

  // 节点圆牌
  drawOperaNode(nodeGroup)

  // 节点文字
  nodeGroup
    .append('text')
    .text((d) => d)
    .attr('x', 0)
    .attr('y', 1)
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('font-size', 11)
    .attr('font-weight', 600)
    .attr('fill', INK)
    .style('font-family', '"STKaiti", "KaiTi", "SimSun", serif')
    .style('letter-spacing', '1px')
    .style('pointer-events', 'none')

  // 节点悬浮效果
  nodeGroup
    .on('mouseenter', function () {
      d3.select(this)
        .transition()
        .duration(180)
        .attr('transform', function (d) {
          const pos = nodePositionMap.get(d)
          return `translate(${pos.x}, ${pos.y}) scale(1.08)`
        })
    })
    .on('mouseleave', function () {
      d3.select(this)
        .transition()
        .duration(180)
        .attr('transform', function (d) {
          const pos = nodePositionMap.get(d)
          return `translate(${pos.x}, ${pos.y}) scale(1)`
        })
    })
}

// 监听下拉框变化，重新绘图
watch(
  () => selectedScriptKey.value,
  async () => {
    await nextTick()
    drawChart()
  },
)

// 监听数据变化，重新绘图
watch(
  () => currentEdges.value,
  async () => {
    await nextTick()
    drawChart()
  },
  { deep: true },
)

onMounted(async () => {
  await loadData()
  await nextTick()
  drawChart()

  resizeObserver = new ResizeObserver(() => {
    drawChart()
  })

  if (chartRef.value) {
    resizeObserver.observe(chartRef.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver && chartRef.value) {
    resizeObserver.unobserve(chartRef.value)
  }
})
</script>

<style scoped>
.chart-one {
  width: 100%;
  height: 100%;
  position: relative;
}

.script-select {
  width: 170px;
  height: 30px;
  margin-bottom: 8px;
  padding: 0 10px;
  border: 1px solid rgba(185, 138, 69, 0.65);
  border-radius: 4px;
  background: rgba(255, 249, 238, 0.92);
  color: #4a2b1a;
  font-size: 13px;
  font-family: "STKaiti", "KaiTi", "SimSun", serif;
  outline: none;
}

.script-select:focus {
  border-color: #b84a36;
  box-shadow: 0 0 0 2px rgba(184, 74, 54, 0.12);
}

.chart-box {
  position: relative;
  width: 100%;
  height: calc(100% - 38px);
  overflow: hidden;
}

.chart-box svg {
  width: 100%;
  height: 100%;
}

.tooltip {
  position: absolute;
  pointer-events: none;
  padding: 8px 10px;
  background: rgba(255, 249, 238, 0.96);
  border: 1px solid rgba(185, 138, 69, 0.75);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.7;
  color: #4a2b1a;
  z-index: 10;
  box-shadow: 0 4px 14px rgba(112, 73, 35, 0.16);
  font-family: "STKaiti", "KaiTi", "SimSun", serif;
}

:deep(.opera-node) {
  cursor: pointer;
}

:deep(.arc-group path) {
  transition: opacity 0.2s ease;
}
</style>