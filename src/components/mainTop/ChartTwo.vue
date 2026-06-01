<template>
  <BaseChart :option="option" />
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from '../BaseChart.vue'

const props = defineProps({
  graph: {
    type: Object,
    required: true,
  },
})

const option = computed(() => ({
  color: ['#8b1d1d', '#256d6a', '#c68a2d', '#4f5d75', '#985f6f'],
  tooltip: {},
  series: [
    {
      type: 'graph',
      layout: 'circular',
      roam: true,
      draggable: true,
      lineStyle: {
        color: 'source',
        opacity: 0.42,
      },
      label: {
        show: true,
        color: '#2d2520',
        fontSize: 11,
      },
      edgeSymbol: ['none', 'arrow'],
      data: props.graph.nodes,
      links: props.graph.links,
    },
  ],
}))
</script>
