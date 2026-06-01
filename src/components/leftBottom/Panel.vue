<template>
  <PanelCard title="主要角色互动弧线图" eyebrow="角色关系网络">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ChartOne v-if="view === 'a'" :arc-relations="arcRelations" />
    <ChartTwo v-else :plays="plays" />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  plays: {
    type: Array,
    required: true,
  },
  arcRelations: {
    type: Object,
    required: true,
  },
})

const view = ref('a')
</script>
