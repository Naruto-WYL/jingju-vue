<template>
  <div ref="rootRef" class="play-select" :class="{ 'is-open': open, 'is-disabled': disabled }">
    <button
      ref="triggerRef"
      class="play-select__trigger"
      type="button"
      :disabled="disabled"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="toggle"
    >
      <span>{{ selectedLabel || placeholder }}</span>
      <i aria-hidden="true"></i>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="menuRef"
        class="play-select__menu"
        role="listbox"
        :style="menuStyle"
      >
        <button
          v-for="option in normalizedOptions"
          :key="option.value"
          type="button"
          class="play-select__option"
          :class="{ selected: option.value === modelValue }"
          role="option"
          :aria-selected="option.value === modelValue"
          @click="pick(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: '',
  },
  options: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: '请选择剧本',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  maxVisible: {
    type: Number,
    default: 5,
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const rootRef = ref(null)
const triggerRef = ref(null)
const menuRef = ref(null)
const open = ref(false)
const menuStyle = ref({})

const normalizedOptions = computed(() =>
  props.options
    .map((option) => {
      if (typeof option === 'string' || typeof option === 'number') {
        return { value: String(option), label: String(option) }
      }
      return {
        value: String(option?.value ?? option?.id ?? ''),
        label: String(option?.label ?? option?.title ?? option?.name ?? ''),
      }
    })
    .filter((option) => option.value && option.label),
)

const selectedLabel = computed(
  () => normalizedOptions.value.find((option) => option.value === String(props.modelValue))?.label || '',
)

onMounted(() => {
  document.addEventListener('pointerdown', handleOutsidePointer)
  window.addEventListener('resize', close)
  window.addEventListener('scroll', close)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleOutsidePointer)
  window.removeEventListener('resize', close)
  window.removeEventListener('scroll', close)
})

async function toggle() {
  if (props.disabled) return
  open.value = !open.value
  if (!open.value) return
  await nextTick()
  positionMenu()
}

function pick(value) {
  emit('update:modelValue', value)
  emit('change', value)
  close()
}

function close() {
  open.value = false
}

function handleOutsidePointer(event) {
  if (!open.value) return
  if (rootRef.value?.contains(event.target) || menuRef.value?.contains(event.target)) return
  close()
}

function positionMenu() {
  const rect = triggerRef.value?.getBoundingClientRect()
  if (!rect) return

  const rowHeight = 30
  const maxHeight = Math.max(rowHeight, props.maxVisible * rowHeight)
  const spaceBelow = window.innerHeight - rect.bottom - 8
  const opensUp = spaceBelow < maxHeight && rect.top > spaceBelow

  menuStyle.value = {
    left: `${Math.max(6, Math.min(rect.left, window.innerWidth - rect.width - 6))}px`,
    top: opensUp ? 'auto' : `${rect.bottom + 3}px`,
    bottom: opensUp ? `${window.innerHeight - rect.top + 3}px` : 'auto',
    width: `${rect.width}px`,
    maxHeight: `${maxHeight}px`,
  }
}
</script>

<style scoped>
.play-select {
  position: relative;
  width: 100%;
  min-width: 0;
}

.play-select__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  min-width: 0;
  height: 100%;
  padding: 0 8px;
  color: inherit;
  font: inherit;
  background: transparent;
  border: 0;
  outline: 0;
  cursor: pointer;
}

.play-select__trigger span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.play-select__trigger i {
  flex: 0 0 auto;
  width: 0;
  height: 0;
  border-top: 5px solid currentColor;
  border-right: 4px solid transparent;
  border-left: 4px solid transparent;
  opacity: 0.72;
}

.is-open .play-select__trigger i {
  transform: rotate(180deg);
}

.is-disabled {
  opacity: 0.55;
}

.play-select__menu {
  position: fixed;
  z-index: 10000;
  overflow-x: hidden;
  overflow-y: auto;
  box-sizing: border-box;
  padding: 2px;
  background: #fffaf0;
  border: 1px solid rgba(142, 47, 36, 0.42);
  border-radius: 6px;
  box-shadow: 0 8px 22px rgba(68, 42, 25, 0.18);
  scrollbar-color: rgba(143, 47, 36, 0.38) #fffaf0;
  scrollbar-width: thin;
}

.play-select__option {
  display: block;
  width: 100%;
  height: 30px;
  padding: 0 9px;
  overflow: hidden;
  color: #50301c;
  font: 800 13px/30px "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}

.play-select__option:hover,
.play-select__option.selected {
  color: #fff8ed;
  background: #8f2f24;
}
</style>
