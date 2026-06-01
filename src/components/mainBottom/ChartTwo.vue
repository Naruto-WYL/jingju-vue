<template>
  <BaseChart :option="trendOption" />
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from '../BaseChart.vue'

const props = defineProps({
  data: {
    type: Array,
    required: true,
  },
})

const trendOption = computed(() => ({
  color: ['#8b1d1d', '#256d6a', '#c68a2d'],
  tooltip: { trigger: 'axis' },
  legend: {
    top: 0,
    textStyle: { color: '#6d5d50' },
  },
  grid: {
    top: 42,
    left: 18,
    right: 18,
    bottom: 14,
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: props.data.map((item) => item.name),
    axisLabel: { color: '#67594e' },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#67594e' },
    splitLine: { lineStyle: { color: 'rgba(111, 87, 73, 0.12)' } },
  },
  series: [
    {
      name: '剧目',
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.14 },
      data: props.data.map((item) => item.playCount),
    },
    {
      name: '场次',
      type: 'bar',
      data: props.data.map((item) => item.sceneCount),
    },
    {
      name: '角色',
      type: 'line',
      smooth: true,
      data: props.data.map((item) => item.characterCount),
    },
  ],
}))
</script>
