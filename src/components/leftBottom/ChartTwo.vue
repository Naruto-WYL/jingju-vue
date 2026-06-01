<template>
  <BaseChart :option="option" />
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from '../BaseChart.vue'

const props = defineProps({
  plays: {
    type: Array,
    required: true,
  },
})

const option = computed(() => ({
  color: ['#256d6a'],
  tooltip: { trigger: 'axis' },
  grid: { top: 18, left: 8, right: 12, bottom: 8, containLabel: true },
  xAxis: {
    type: 'category',
    data: props.plays.map((play) => play.title),
    axisLabel: { color: '#667b99', rotate: 28, width: 70, overflow: 'truncate' },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#667b99' },
    splitLine: { lineStyle: { color: 'rgba(39, 59, 88, 0.12)' } },
  },
  series: [
    {
      name: '互动指数',
      type: 'bar',
      data: props.plays.map((play) => play.score),
      itemStyle: { borderRadius: [5, 5, 0, 0] },
    },
  ],
}))
</script>
