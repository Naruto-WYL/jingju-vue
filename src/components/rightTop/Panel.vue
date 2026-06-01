<template>
  <PanelCard title="跨剧本主题组合" eyebrow="核心主题、剧本组合与共现强度">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ThemeRingChartOne v-if="view === 'a'" />
    <ThemeRingChartTwo v-else />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ThemeRingChartOne from './ChartOne.vue'
import ThemeRingChartTwo from './ChartTwo.vue'

defineProps({
  data: {
    type: Array,
    required: true,
  },
})

const view = ref('a')
</script>
