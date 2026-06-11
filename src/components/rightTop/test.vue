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
const MAIN_COLOR = '#DDCCAB'

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

// 绘图
function drawChart() {
  const container = chartRef.value
  const svgEl = svgRef.value

  if (!container || !svgEl) return

  const width = container.clientWidth
  const height = container.clientHeight

  const svg = d3.select(svgEl)

  svg.selectAll('*').remove()

  svg
    .attr('width', width)
    .attr('height', height)

  const edges = currentEdges.value

  if (!edges.length || width <= 0 || height <= 0) return

  const margin = {
    top: 30,
    right: 10,
    bottom: 70,
    left: 10,
  }

  const baseY = height - margin.bottom

  // 获取所有角色节点
  const roleSet = new Set()

  edges.forEach((edge) => {
    roleSet.add(edge.source)
    roleSet.add(edge.target)
  })

  const roles = Array.from(roleSet)

  const xScale = d3
    .scalePoint()
    .domain(roles)
    .range([margin.left, width - margin.right])
    .padding(0.01)

  const maxWeight = d3.max(edges, (d) => d.weight) || 1
  const minWeight = d3.min(edges, (d) => d.weight) || 1

  /**
   * 这里是核心：
   * 权重越大，弧线离 baseY 越远。
   * 不再用 stroke-width 表示权重。
   *
   * range 第一个值：最小权重的弧线高度
   * range 第二个值：最大权重的弧线高度
   */
  const arcDistanceScale = d3
    .scaleLinear()
    .domain([minWeight, maxWeight])
    .range([height * 0.2, height * 1.5])
  // 固定线宽，不让线宽代表权重
  const FIXED_LINE_WIDTH = 2.2

  // 生成弧线路径
  function getArcPath(edge, index) {
  const x1 = xScale(edge.source)
  const x2 = xScale(edge.target)
  if (x1 == null || x2 == null) return ''

  const midX = (x1 + x2) / 2
  const xDistance = Math.abs(x2 - x1)

  // 权重基础高度
  const weightDistance = arcDistanceScale(edge.weight)

  // 让长弧稍微高一点
  const distanceBonus = xDistance * 0.15

  // 给相近边增加一点错位，避免全部重叠
  const layerOffset = (index % 5) * 18

  const arcDistance = weightDistance + distanceBonus + layerOffset
  const controlY = baseY - arcDistance

  return `M ${x1},${baseY} Q ${midX},${controlY} ${x2},${baseY}`
}

  // 画弧线
  svg
    .append('g')
    .attr('class', 'arc-group')
    .selectAll('path')
    .data(edges)
    .join('path')
    .attr('d', (d, i) => getArcPath(d, i))
    .attr('fill', 'none')
    .attr('stroke', MAIN_COLOR)
    .attr('stroke-width', FIXED_LINE_WIDTH)
    .attr('opacity', 0.65)
    .attr('cursor', 'pointer')
    .attr('stroke-linecap', 'round')
    .on('mouseenter', function (event, d) {
      d3.select(this)
        .attr('opacity', 1)
        .attr('stroke-width', FIXED_LINE_WIDTH + 1)

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
    .on('mouseleave', function () {
      d3.select(this)
        .attr('opacity', 0.65)
        .attr('stroke-width', FIXED_LINE_WIDTH)

      tooltip.show = false
    })

  // 画节点
  const nodeGroup = svg
    .append('g')
    .attr('class', 'node-group')
    .selectAll('g')
    .data(roles)
    .join('g')
    .attr('class', 'opera-node')
    .attr('transform', (d) => `translate(${xScale(d)}, ${baseY})`)

  nodeGroup
    .append('circle')
    .attr('r', 6)
    .attr('fill', '#fff')
    .attr('stroke', MAIN_COLOR)
    .attr('stroke-width', 2.2)

  nodeGroup
    .append('circle')
    .attr('r', 3.2)
    .attr('fill', MAIN_COLOR)

  nodeGroup
    .append('text')
    .text((d) => d)
    .attr('x', 3)
    .attr('y', 10)
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 8)
    .attr('fill', '#777')
    .attr('writing-mode', 'vertical-rl')
    .attr('glyph-orientation-vertical', 0)
    .style('letter-spacing', '2px')
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