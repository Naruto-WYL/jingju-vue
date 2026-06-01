<template>
  <div class="metric-strip">
    <article v-for="item in metrics" :key="item.label" class="metric">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </article>
  </div>
</template>

<script setup>
defineProps({
  metrics: {
    type: Array,
    required: true,
  },
})
</script>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.metric {
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(39, 59, 88, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.54);
}

.metric span {
  display: block;
  color: #75675c;
  font-size: 12px;
}

.metric strong {
  display: block;
  margin-top: 4px;
  color: #273b58;
  font-size: 22px;
  line-height: 1;
}
</style>
