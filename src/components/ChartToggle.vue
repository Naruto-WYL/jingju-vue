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
  border: 1px solid rgba(143, 47, 36, 0.48);
  border-radius: 999px;
  color: #7a241d;
  background: #FBF6E9;
  box-shadow: inset 0 0 0 1px rgba(255, 248, 232, 0.74);
  cursor: pointer;
}

.chart-toggle span {
  display: grid;
  place-items: center;
  height: 20px;
  border-radius: 999px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.chart-toggle .active {
  color: #7a241d;
  background: #FBF6E9;
}
</style>
