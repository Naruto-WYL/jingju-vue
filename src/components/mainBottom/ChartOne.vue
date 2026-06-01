<template>
  <BaseChart :option="riverOption" />
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from '../BaseChart.vue'

const progressPoints = [
  { label: '开端', value: 0 },
  { label: '引入', value: 15 },
  { label: '铺陈', value: 30 },
  { label: '发展', value: 45 },
  { label: '冲突', value: 60 },
  { label: '高潮', value: 75 },
  { label: '转折', value: 90 },
  { label: '收束', value: 100 },
]

const narrativeSeries = {
  唱: [12, 18, 28, 24, 18, 30, 16, 12],
  念: [18, 20, 16, 14, 22, 18, 12, 10],
  白: [26, 22, 18, 20, 24, 16, 14, 12],
  做: [8, 12, 16, 22, 20, 26, 18, 10],
  打: [2, 4, 8, 10, 22, 30, 16, 4],
  冲突: [3, 8, 14, 22, 36, 40, 18, 6],
  情绪: [10, 18, 24, 30, 34, 42, 36, 20],
  转折: [0, 2, 6, 8, 14, 20, 34, 16],
  群体出场: [18, 10, 12, 16, 22, 28, 14, 8],
  核心人物出现: [24, 26, 28, 32, 34, 38, 30, 22],
}

const progressLabelMap = Object.fromEntries(progressPoints.map((item) => [item.value, item.label]))

const riverOption = computed(() => ({
  color: ['#8b2a25', '#c28732', '#2f6f6d', '#6d597a', '#b56576', '#7f5539', '#d07a3f', '#4f5b7c', '#789262', '#9b5f6d'],
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'line' },
    formatter: (params) => {
      const progress = params[0]?.data?.[0]
      const title = `${progressLabelMap[progress] || `${progress}%`} / 剧情进度 ${progress}%`
      const body = params
        .slice()
        .sort((a, b) => b.data[1] - a.data[1])
        .map((item) => `${item.marker}${item.seriesName}：${item.data[1]}`)
        .join('<br/>')
      return `${title}<br/>${body}`
    },
  },
  legend: {
    top: 0,
    right: 8,
    itemWidth: 10,
    itemHeight: 8,
    textStyle: { color: '#66584d', fontSize: 10 },
  },
  grid: {
    top: 42,
    left: 58,
    right: 24,
    bottom: 24,
    containLabel: true,
  },
  xAxis: {
    type: 'value',
    min: 0,
    max: 100,
    name: '剧情进度',
    nameTextStyle: { color: '#67594e', fontSize: 11 },
    axisLabel: {
      color: '#67594e',
      fontSize: 11,
      formatter: (value) => progressLabelMap[value] || `${value}%`,
    },
    axisLine: { lineStyle: { color: 'rgba(88, 68, 51, 0.28)' } },
    splitLine: { lineStyle: { color: 'rgba(88, 68, 51, 0.08)' } },
  },
  yAxis: {
    type: 'value',
    name: '叙事强度 / 表演密度',
    nameLocation: 'middle',
    nameGap: 42,
    nameTextStyle: { color: '#67594e', fontSize: 11, fontWeight: 700 },
    axisLabel: { color: '#67594e', fontSize: 10 },
    axisLine: { show: true, lineStyle: { color: 'rgba(88, 68, 51, 0.28)' } },
    splitLine: { lineStyle: { color: 'rgba(88, 68, 51, 0.1)' } },
  },
  series: Object.entries(narrativeSeries).map(([name, values]) => ({
    name,
    type: 'line',
    stack: '叙事成分',
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 0 },
    areaStyle: { opacity: 0.78 },
    emphasis: { focus: 'series' },
    data: values.map((value, index) => [progressPoints[index].value, value]),
  })),
}))
</script>
