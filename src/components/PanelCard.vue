<template>
  <section class="panel-card" :class="{ compact }">
    <header class="panel-card__header">
      <div>
        <p v-if="eyebrow" class="panel-card__eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <slot name="action" />
    </header>
    <div class="panel-card__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  eyebrow: {
    type: String,
    default: '',
  },
  compact: {
    type: Boolean,
    default: false,
  },
})
</script>

<style scoped>
.panel-card {
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 12px;
  overflow: hidden;
  border: 0;
  border-radius: 10px;
  background: transparent;
  box-shadow: none;
}

.panel-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-height: 34px;
  margin-bottom: 6px;
}

.panel-card__eyebrow {
  margin: 0 0 4px;
  color: #4a6384;
  font-size: 12px;
  font-weight: 700;
}

.panel-card h2 {
  margin: 0;
  color: #273b58;
  font-size: 16px;
  line-height: 1.15;
  letter-spacing: 0;
}

.panel-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: calc(100% - 40px);
  min-height: 0;
}

@media (max-width: 980px) {
  .panel-card {
    min-height: 340px;
  }
}
</style>
