<template>
  <button class="chart-toggle" type="button" :aria-pressed="modelValue === 'b'" @click="toggle">
    <span :class="{ active: modelValue === 'a' }">图一</span>
    <span :class="{ active: modelValue === 'b' }">图二</span>
  </button>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

function toggle() {
  emit('update:modelValue', props.modelValue === 'a' ? 'b' : 'a')
}
</script>

<style scoped>
.chart-toggle {
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  width: 74px;
  height: 26px;
  padding: 2px;
  border: 1px solid rgba(39, 59, 88, 0.18);
  border-radius: 999px;
  color: #5d718f;
  background: rgba(255, 255, 255, 0.58);
  cursor: pointer;
}

.chart-toggle span {
  display: grid;
  place-items: center;
  height: 20px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}

.chart-toggle .active {
  color: #ffffff;
  background: #273b58;
}
</style>
