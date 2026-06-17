<template>
  <section class="panel-card" :class="{ compact }">
    <header
      v-if="hasHeader"
      class="panel-card__header"
      :class="{ 'panel-card__header--action-only': !hasTitleBlock }"
    >
      <div v-if="hasTitleBlock">
        <p v-if="eyebrow" class="panel-card__eyebrow">{{ eyebrow }}</p>
        <h2 v-if="title">{{ title }}</h2>
      </div>
      <slot name="action" />
    </header>
    <div class="panel-card__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '',
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

const slots = useSlots()
const hasTitleBlock = computed(() => Boolean(props.title || props.eyebrow))
const hasHeader = computed(() => hasTitleBlock.value || Boolean(slots.action))
</script>

<style scoped>
.panel-card {
  position: relative;
  display: flex;
  flex-direction: column;
  isolation: isolate;
  min-width: 0;
  min-height: 0;
  height: 100%;
  padding: 12px 12px 10px;
  overflow: hidden;
  border: 1px solid rgba(143, 47, 36, 0.58);
  border-radius: 2px;
  background:
    linear-gradient(180deg, rgba(255, 251, 241, 0.88), rgba(246, 235, 213, 0.76)),
    #f7edd8;
  box-shadow:
    inset 0 0 0 1px rgba(198, 121, 73, 0.14),
    0 0 0 1px rgba(255, 248, 232, 0.5);
}

.panel-card::before,
.panel-card::after {
  position: absolute;
  content: "";
  pointer-events: none;
}

.panel-card::before {
  inset: 5px;
  z-index: -1;
  border: 1px solid rgba(143, 47, 36, 0.2);
}

.panel-card::after {
  inset: 0;
  z-index: 2;
  background:
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px top 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px top 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) left 4px bottom 4px / 1px 26px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 26px 1px no-repeat,
    linear-gradient(#a84d36, #a84d36) right 4px bottom 4px / 1px 26px no-repeat;
  opacity: 0.72;
}

.panel-card__header {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex: 0 0 auto;
  min-height: 42px;
  margin-bottom: 6px;
  padding: 0 2px 7px;
  border-bottom: 1px solid rgba(143, 47, 36, 0.3);
}

.panel-card__header--action-only {
  justify-content: flex-end;
  min-height: 30px;
  margin-bottom: 4px;
  padding: 0 2px;
  border-bottom: 0;
}

.panel-card__eyebrow {
  margin: 0 0 3px;
  color: #7a241d;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.1;
}

.panel-card h2 {
  margin: 0;
  color: #5b1e17;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.12;
  letter-spacing: 0;
}

.panel-card__body {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 4px;
  height: auto;
  min-height: 0;
}

@media (max-width: 980px) {
  .panel-card {
    min-height: 340px;
  }
}
</style>
