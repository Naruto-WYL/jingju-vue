<template>
  <PanelCard title="行当推断与特征模式" eyebrow="未标注角色识别">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ChartOne v-if="view === 'a'" :stats="stats" />
    <ChartTwo v-else />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  stats: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
</script>
