<template>
  <div class="role-filter-bar">
    <label>
      <span>历史时期</span>
      <select v-model="filters.era">
        <option v-for="item in safeOptions.eras" :key="item" :value="item">{{ item }}</option>
      </select>
    </label>

    <label>
      <span>行当</span>
      <select v-model="filters.role">
        <option v-for="item in safeOptions.roles" :key="item" :value="item">{{ item }}</option>
      </select>
    </label>

    <label>
      <span>标注状态</span>
      <select v-model="filters.status">
        <option v-for="item in safeOptions.statuses" :key="item" :value="item">{{ item }}</option>
      </select>
    </label>

    <label>
      <span>搜索角色 / 剧目</span>
      <input v-model.trim="filters.keyword" type="search" placeholder="如 诸葛亮、空城计、苏三" />
    </label>
  </div>

  <div class="role-explain">
    <strong>{{ explanation.title }}</strong>
    <span>{{ explanation.detail }}</span>
  </div>

  <BaseChart class="role-heatmap" :option="heatmapOption" />
</template>

<script setup>
import { computed, reactive } from 'vue'
import BaseChart from '../BaseChart.vue'

const props = defineProps({
  stats: {
    type: Object,
    required: true,
  },
})

const filters = reactive({
  era: '全部时期',
  role: '全部行当',
  status: '全部角色',
  keyword: '',
})

const safeOptions = computed(() => ({
  eras: props.stats.filterOptions?.eras?.length ? props.stats.filterOptions.eras : ['全部时期'],
  roles: props.stats.filterOptions?.roles?.length ? props.stats.filterOptions.roles : ['全部行当'],
  statuses: props.stats.filterOptions?.statuses?.length ? props.stats.filterOptions.statuses : ['全部角色'],
}))

const mockRoleFeatureRecords = [
  { role: '旦', feature: '女性闺阁', status: '推断角色' },
  { role: '旦', feature: '女性闺阁', status: '已标注' },
  { role: '生', feature: '书生公子', status: '推断角色' },
  { role: '生', feature: '帝王皇族', status: '已标注' },
  { role: '净', feature: '将帅武人', status: '推断角色' },
  { role: '丑', feature: '市井滑稽', status: '推断角色' },
]

const filteredRecords = computed(() => {
  const keyword = filters.keyword.toLowerCase()

  return (props.stats.roleFeatureRecords || []).filter((item) => {
    const matchedEra = filters.era === '全部时期' || item.era === filters.era
    const matchedRole = filters.role === '全部行当' || item.role === filters.role
    const matchedStatus = filters.status === '全部角色' || item.status === filters.status
    const matchedKeyword = !keyword || `${item.name}${item.feature}`.toLowerCase().includes(keyword)

    return matchedEra && matchedRole && matchedStatus && matchedKeyword
  })
})

const heatmapShape = computed(() => {
  const records = filteredRecords.value.length ? filteredRecords.value : mockRoleFeatureRecords
  const roles = topValues(records, 'role', 6)
  const features = topValues(records, 'feature', 8)
  const roleIndex = new Map(roles.map((role, index) => [role, index]))
  const featureIndex = new Map(features.map((feature, index) => [feature, index]))
  const matrix = new Map()

  records.forEach((item) => {
    if (!roleIndex.has(item.role) || !featureIndex.has(item.feature)) return

    const key = `${featureIndex.get(item.feature)}-${roleIndex.get(item.role)}`
    matrix.set(key, (matrix.get(key) || 0) + 1)
  })

  return {
    roles,
    features,
    values: Array.from(matrix.entries()).map(([key, value]) => {
      const [x, y] = key.split('-').map(Number)
      return [x, y, value]
    }),
  }
})

const explanation = computed(() => {
  const records = filteredRecords.value.length ? filteredRecords.value : mockRoleFeatureRecords
  const inferred = records.filter((item) => item.status === '推断角色').length
  const topCell = heatmapShape.value.values.slice().sort((a, b) => b[2] - a[2])[0]

  if (!topCell) {
    return {
      title: '暂无匹配样本',
      detail: '请调整历史时期、行当、标注状态或搜索条件。',
    }
  }

  const feature = heatmapShape.value.features[topCell[0]]
  const role = heatmapShape.value.roles[topCell[1]]

  return {
    title: `当前筛选 ${records.length} 个角色，其中推断角色 ${inferred} 个`,
    detail: `最明显的对应模式是“${feature}”集中出现在“${role}”行当。`,
  }
})

const heatmapOption = computed(() => {
  const maxValue = Math.max(1, ...heatmapShape.value.values.map((item) => item[2]))

  return {
    tooltip: {
      position: 'top',
      formatter: (params) => {
        const feature = heatmapShape.value.features[params.value[0]]
        const role = heatmapShape.value.roles[params.value[1]]
        return `${role} / ${feature}<br/>角色数：${params.value[2]}`
      },
    },
    grid: {
      top: 26,
      left: 4,
      right: 8,
      bottom: 4,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: heatmapShape.value.features,
      splitArea: { show: true },
      axisLabel: {
        color: '#3d3935',
        interval: 0,
        rotate: 24,
        width: 62,
        overflow: 'truncate',
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'category',
      data: heatmapShape.value.roles,
      splitArea: { show: true },
      axisLabel: { color: '#3d3935', fontSize: 11 },
    },
    visualMap: {
      show: true,
      min: 0,
      max: maxValue,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      top: -15,
      itemWidth: 10,
      itemHeight: 480,
      text: ['高', '低'],
      textStyle: {
        color: '#6c6259',
        fontSize: 10,
      },
      inRange: {
        color: ['#f8efe2', '#efd2aa', '#d98a52', '#b83b31', '#6f1418'],
      },
    },
    series: [
      {
        name: '特征-行当热力',
        type: 'heatmap',
        data: heatmapShape.value.values,
        label: {
          show: true,
          color: '#382b25',
          fontSize: 10,
        },
        emphasis: {
          itemStyle: {
            borderColor: '#6f1418',
            borderWidth: 1,
          },
        },
      },
    ],
  }
})

function topValues(records, key, limit) {
  const counts = records.reduce((map, item) => {
    map.set(item[key], (map.get(item[key]) || 0) + 1)
    return map
  }, new Map())

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name]) => name)
}
</script>

<style scoped>
.role-filter-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  flex: 0 0 auto;
}

.role-filter-bar label {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.role-filter-bar span {
  color: #536984;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.role-filter-bar select,
.role-filter-bar input {
  width: 100%;
  height: 24px;
  min-width: 0;
  padding: 0 7px;
  border: 1px solid rgba(39, 59, 88, 0.16);
  border-radius: 5px;
  outline: none;
  color: #273b58;
  background: rgba(255, 255, 255, 0.68);
  font-size: 11px;
}

.role-filter-bar input::placeholder {
  color: #8090a6;
}

.role-explain {
  display: grid;
  gap: 2px;
  flex: 0 0 auto;
  padding: 5px 8px;
  border: 1px solid rgba(39, 59, 88, 0.12);
  border-radius: 6px;
  color: #324761;
  background: rgba(255, 255, 255, 0.5);
}

.role-explain strong {
  font-size: 11px;
  line-height: 1.15;
}

.role-explain span {
  color: #5c6f89;
  font-size: 11px;
  line-height: 1.2;
}

.role-heatmap {
  min-height: 0;
}

@media (max-width: 980px) {
  .role-filter-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
