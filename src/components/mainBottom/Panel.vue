<template>
  <PanelCard title="阶段主题河流" eyebrow="剧目数量、场次与角色规模">
    <template #action>
      <ChartToggle v-model="view" />
    </template>

    <ChartOne v-if="view === 'a'" />
    <ChartTwo v-else :data="data" />
  </PanelCard>
</template>

<script setup>
import { ref } from 'vue'
import ChartToggle from '../ChartToggle.vue'
import PanelCard from '../PanelCard.vue'
import ChartOne from './ChartOne.vue'
import ChartTwo from './ChartTwo.vue'

defineProps({
  data: {
    type: Array,
    required: true,
  },
})

const view = ref('a')
</script>
