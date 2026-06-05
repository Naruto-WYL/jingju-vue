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

const DATA_URL = '/数据表合集/2/p2_one.xlsx'
const MAIN_COLOR = '#DDCCAB'

function normalizeKey(key) {
  return String(key || '').replace(/\s+/g, '').toLowerCase()
}

function pickValue(row, candidates) {
  const keyMap = new Map(
    Object.keys(row).map((key) => [normalizeKey(key), key]),
  )

  for (const candidate of candidates) {
    const key = keyMap.get(normalizeKey(candidate))

    if (key && row[key] !== '') {
      return row[key]
    }
  }

  return ''
}

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
        script_id: String(pickValue(row, ['剧本ID', '剧本id', 'script_id']) || '').trim(),
        script_title: String(pickValue(row, ['剧本名称', 'script_title']) || '').trim(),
        source: String(pickValue(row, ['角色A', '角色a', 'source']) || '').trim(),
        target: String(pickValue(row, ['角色B', '角色b', 'target']) || '').trim(),
        weight: Number(pickValue(row, ['关系强度', 'weight']) || 0),
        relation_type: String(pickValue(row, ['关系类型', 'relation_type']) || '').trim(),
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
    top: 46,
    right: 72,
    bottom: 46,
    left: 72,
  }

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
  // 想让圆圈更大，改成 0.43 / 0.45
  // 想让圆圈更小，改成 0.35 / 0.38
  const radius = Math.min(
    width - margin.left - margin.right,
    height - margin.top - margin.bottom,
  ) * 0.55

  // 计算角色关系数量
  // 关系多的角色优先排布，使整体更均衡
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
    // 从正上方开始排
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
  // 想让粗细差异更明显，就把 range 改成 [1, 8]
  // 想让线不要太粗，就把 range 改成 [1, 4]
  const lineWidthScale = d3
    .scaleLinear()
    .domain([minWeight, maxWeight])
    .range([1.2, 6])

  // 弧线弯曲程度
  // 数值越大，线越往圆心靠
  const CURVE_RATIO = 0.58

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

    // 控制点朝圆心移动，形成圆内弧线
    const controlX = midX + (centerX - midX) * CURVE_RATIO
    const controlY = midY + (centerY - midY) * CURVE_RATIO

    // 少量错位，防止完全重合
    const offset = ((index % 5) - 2) * 4

    return `
      M ${x1},${y1}
      Q ${controlX + offset},${controlY + offset}
        ${x2},${y2}
    `
  }

  // 背景圆圈
  svg
    .append('circle')
    .attr('cx', centerX)
    .attr('cy', centerY)
    .attr('r', radius)
    .attr('fill', 'none')
    .attr('stroke', "#DD7298")
    .attr('stroke-width', 1.2)
    .attr('opacity', 0.36)
    .attr('stroke-dasharray', '6 2')

  // 画关系线
  svg
    .append('g')
    .attr('class', 'arc-group')
    .selectAll('path')
    .data(edges)
    .join('path')
    .attr('d', (d, i) => getArcPath(d, i))
    .attr('fill', 'none')
    .attr('stroke', "#E0D1B7")
    .attr('stroke-width', (d) => lineWidthScale(d.weight))
    .attr('opacity', 0.5)
    .attr('cursor', 'pointer')
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .on('mouseenter', function (event, d) {
      d3.select(this)
        .attr('opacity', 0.95)
        .attr('stroke-width', lineWidthScale(d.weight) + 1.5)

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
        .attr('opacity', 0.5)
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

  // 节点外圈
  nodeGroup
    .append('circle')
    .attr('r', 7)
    .attr('fill', '#fff')
    .attr('stroke', MAIN_COLOR)
    .attr('stroke-width', 2.2)

  // 节点内点
  nodeGroup
    .append('circle')
    .attr('r', 3.6)
    .attr('fill', MAIN_COLOR)

  // 节点文字
  nodeGroup
    .append('text')
    .text((d) => d)
    .attr('x', (d) => {
      const pos = nodePositionMap.get(d)

      // 文字沿圆心向外偏移
      return Math.cos(pos.angle) * 14
    })
    .attr('y', (d) => {
      const pos = nodePositionMap.get(d)

      // 文字沿圆心向外偏移
      return Math.sin(pos.angle) * 14
    })
    .attr('text-anchor', (d) => {
      const pos = nodePositionMap.get(d)
      const cos = Math.cos(pos.angle)

      if (Math.abs(cos) < 0.25) {
        return 'middle'
      }

      return cos > 0 ? 'start' : 'end'
    })
    .attr('dominant-baseline', (d) => {
      const pos = nodePositionMap.get(d)
      const sin = Math.sin(pos.angle)

      if (sin < -0.6) return 'baseline'
      if (sin > 0.6) return 'hanging'

      return 'middle'
    })
    .attr('font-size', 10)
    .attr('fill', '#777')
    .style('letter-spacing', '1px')
    .style('pointer-events', 'none')
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
}

.script-select {
  width: 160px;
  height: 30px;
  margin-bottom: 8px;
}

.chart-box {
  position: relative;
  width: 100%;
  height: calc(100% - 38px);
}

.chart-box svg {
  width: 100%;
  height: 100%;
}

.tooltip {
  position: absolute;
  pointer-events: none;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #ccc;
  font-size: 12px;
  color: #333;
  z-index: 10;
}

:deep(.opera-node) {
  cursor: pointer;
}
</style>
