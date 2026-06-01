<template>
  <PanelCard title="角色关系网络" eyebrow="共场、对话、共同动作">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ChartOne v-if="view === 'a'" :graph="graph" />
    <ChartTwo v-else :graph="graph" />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  graph: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
</script>
