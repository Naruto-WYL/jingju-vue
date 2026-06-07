<template>
  <section class="theme-card-view" aria-label="剧本主题构成">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>
    <div v-else-if="error" class="theme-state theme-state--error">{{ error }}</div>

    <div v-else class="theme-content">
      <div class="replace-toolbar">
        <label class="replace-field">
          <span>替换卡片</span>
          <select v-model="targetPlayId" :disabled="!visiblePlays.length">
            <option v-for="play in visiblePlays" :key="play.playId" :value="play.playId">
              {{ play.title }}
            </option>
          </select>
        </label>

        <label class="replace-field">
          <span>换入剧本</span>
          <select v-model="replacementPlayId" :disabled="!hiddenPlayOptions.length">
            <option v-for="play in hiddenPlayOptions" :key="play.playId" :value="play.playId">
              {{ play.title }}
            </option>
          </select>
        </label>

        <button class="replace-button" type="button" :disabled="!targetPlayId || !replacementPlayId" @click="replaceSelectedPlay">
          执行替换
        </button>
      </div>

      <div class="script-scroll">
        <article
          v-for="(play, index) in visiblePlays"
          :key="play.playId"
          class="script-theme-card"
        >
          <div class="script-name-block">
            <strong>{{ play.title }}</strong>
            <span>{{ eraLabel(play.genre) }}</span>
          </div>

          <svg
            :ref="(el) => setChartRef(el, index)"
            class="theme-bars"
            role="img"
            :aria-label="`${play.title}主题构成`"
          />
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import * as d3 from 'd3'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { groupRowsByPlay, useThemeCsv } from './themeCsv'

const { rows, loading, error } = useThemeCsv()

const CARD_COUNT = 5
const KAI_FONT = '"STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif'
const chartRefs = ref([])
const displayedPlayIds = ref([])
const targetPlayId = ref('')
const replacementPlayId = ref('')

let resizeObserver = null

const themePalette = [
  '#b64234',
  '#8f5f2f',
  '#315f5a',
  '#4f5f87',
  '#8a4f68',
]

const plays = computed(() =>
  groupRowsByPlay(rows.value).filter(
    (play) => play.playId && play.title && play.themes.length,
  ),
)

const playMap = computed(() => new Map(plays.value.map((play) => [play.playId, play])))

const playOptions = computed(() =>
  plays.value
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)),
)

const visiblePlays = computed(() =>
  displayedPlayIds.value
    .map((playId) => playMap.value.get(playId))
    .filter(Boolean),
)

const hiddenPlayOptions = computed(() => {
  const visibleIds = new Set(displayedPlayIds.value)
  return playOptions.value.filter((play) => !visibleIds.has(play.playId))
})

watch(
  plays,
  () => {
    reconcileDisplayedPlays()
  },
  { immediate: true },
)

watch(
  visiblePlays,
  async () => {
    await nextTick()
    observeCharts()
    renderThemeBars()
    syncReplacementSelect()
  },
  { deep: true, flush: 'post' },
)

watch(targetPlayId, () => {
  syncReplacementSelect()
})

onMounted(() => {
  resizeObserver = new ResizeObserver(() => renderThemeBars())
  observeCharts()
  renderThemeBars()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

function setChartRef(el, index) {
  chartRefs.value[index] = el || null
}

function observeCharts() {
  if (!resizeObserver) return

  resizeObserver.disconnect()

  chartRefs.value.forEach((element) => {
    if (element) resizeObserver.observe(element)
  })
}

function reconcileDisplayedPlays() {
  if (!plays.value.length) {
    displayedPlayIds.value = []
    return
  }

  const validIds = new Set(plays.value.map((play) => play.playId))
  const nextIds = displayedPlayIds.value
    .filter((playId) => validIds.has(playId))
    .slice(0, CARD_COUNT)

  const usedIds = new Set(nextIds)

  playOptions.value.forEach((play) => {
    if (nextIds.length >= CARD_COUNT || usedIds.has(play.playId)) return

    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  displayedPlayIds.value = nextIds
  chartRefs.value = chartRefs.value.slice(0, CARD_COUNT)

  if (!targetPlayId.value || !nextIds.includes(targetPlayId.value)) {
    targetPlayId.value = nextIds[0] || ''
  }

  syncReplacementSelect()
}

function replaceSelectedPlay() {
  if (!targetPlayId.value || !replacementPlayId.value) return

  const targetIndex = displayedPlayIds.value.indexOf(targetPlayId.value)
  if (targetIndex === -1) return

  const nextIds = displayedPlayIds.value.slice()
  nextIds[targetIndex] = replacementPlayId.value
  displayedPlayIds.value = nextIds
  targetPlayId.value = replacementPlayId.value

  nextTick(() => {
    syncReplacementSelect()
    renderThemeBars()
  })
}

function syncReplacementSelect() {
  if (!hiddenPlayOptions.value.length) {
    replacementPlayId.value = ''
    return
  }

  if (!hiddenPlayOptions.value.some((play) => play.playId === replacementPlayId.value)) {
    replacementPlayId.value = hiddenPlayOptions.value[0].playId
  }
}

function renderThemeBars() {
  visiblePlays.value.forEach((play, index) => {
    drawThemeBars(chartRefs.value[index], play)
  })
}

function drawThemeBars(svgElement, play) {
  if (!svgElement) return

  const themes = normalizedThemes(play).slice(0, 5)
  const width = Math.max(260, Math.round(svgElement.clientWidth || 320))
  const height = 76

  const columns = 2
  const columnGap = 20
  const rowGap = 36
  const itemWidth = (width - columnGap) / columns

  const dotX = 4
  const labelX = 15
  const labelY = 6
  const barX = 4
  const barY = 25
  const percentWidth = 34
  const barWidth = Math.max(48, itemWidth - barX - percentWidth - 8)

  const maxShare = Math.max(0.01, d3.max(themes, (theme) => theme.share) || 0)

  const svg = d3.select(svgElement)

  svg.selectAll('*').remove()

  svg
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'none')

  const rows = svg
    .selectAll('g.theme-row')
    .data(themes)
    .join('g')
    .attr('class', 'theme-row')
    .attr('transform', (_, index) => {
      const column = index % columns
      const row = Math.floor(index / columns)
      return `translate(${column * (itemWidth + columnGap)},${5 + row * rowGap})`
    })

  rows.append('title').text((theme) => `${themeLabel(theme.name)}：${Math.round(theme.share * 100)}%`)

  rows
    .append('circle')
    .attr('cx', dotX)
    .attr('cy', labelY)
    .attr('r', 3.4)
    .attr('fill', (theme, index) => themePalette[index % themePalette.length])
    .attr('stroke', '#f8ead2')
    .attr('stroke-width', 1.4)

  rows
    .append('text')
    .attr('x', labelX)
    .attr('y', labelY)
    .attr('dy', '0.36em')
    .attr('text-anchor', 'start')
    .attr('fill', '#3d2a21')
    .attr('font-family', KAI_FONT)
    .attr('font-size', 16)
    .attr('font-weight', 900)
    .text((theme) => shortThemeLabel(theme.name))

  rows
    .append('line')
    .attr('x1', barX)
    .attr('x2', barX + barWidth)
    .attr('y1', barY)
    .attr('y2', barY)
    .attr('stroke', 'rgba(92, 61, 38, 0.16)')
    .attr('stroke-width', 4.4)
    .attr('stroke-linecap', 'round')

  rows
    .append('line')
    .attr('x1', barX)
    .attr('x2', (theme) => barX + (theme.share / maxShare) * barWidth)
    .attr('y1', barY)
    .attr('y2', barY)
    .attr('stroke', (theme, index) => themePalette[index % themePalette.length])
    .attr('stroke-width', 4.8)
    .attr('stroke-linecap', 'round')

  rows
    .append('circle')
    .attr('cx', (theme) => barX + (theme.share / maxShare) * barWidth)
    .attr('cy', barY)
    .attr('r', 2.3)
    .attr('fill', '#fff7e8')
    .attr('stroke', (theme, index) => themePalette[index % themePalette.length])
    .attr('stroke-width', 1.4)

  rows
    .append('text')
    .attr('x', itemWidth)
    .attr('y', barY)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('fill', '#503225')
    .attr('font-family', KAI_FONT)
    .attr('font-size', 13)
    .attr('font-weight', 1200)
    .text((theme) => `${Math.round(theme.share * 100)}%`)
}

function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)
  const total = validThemes.reduce((sum, theme) => sum + Number(theme.share || 0), 0) || 1

  return validThemes.map((theme) => ({
    ...theme,
    share: Number(theme.share || 0) / total,
  }))
}

function dominantShare(play) {
  return Math.max(0, ...play.themes.map((theme) => Number(theme.share || 0)))
}

function eraLabel(genre) {
  const value = String(genre || '').trim()

  if (!value) return '未知'
  if (value === '三国') return '三国时期'
  if (value === '东汉') return '汉代'

  return value
}

function themeLabel(name) {
  const value = String(name || '').trim()

  if (!value) return '未识别'

  return /^\d+$/.test(value) ? `主题${value}` : value
}

function shortThemeLabel(name) {
  const value = themeLabel(name)

  if (value.length <= 4) return value

  return `${value.slice(0, 4)}`
}
</script>

<style scoped>
.theme-card-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #39251c;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.theme-content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.replace-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 72px;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  min-height: 26px;
}

.replace-field {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.replace-field span {
  color: #6b352b;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.replace-field select {
  width: 100%;
  height: 24px;
  min-width: 0;
  padding: 0 18px 0 7px;
  border: 1px solid rgba(92, 61, 38, 0.2);
  border-radius: 6px;
  outline: none;
  color: #3d2a21;
  font-family: inherit;
  font-size: 12px;
  font-weight: 900;
  background: rgba(255, 249, 235, 0.82);
}

.replace-button {
  width: 100%;
  height: 24px;
  border: 0;
  border-radius: 6px;
  color: #fff8ed;
  font-family: inherit;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  background: linear-gradient(180deg, #b64234, #8f2f24);
  box-shadow: 0 4px 9px rgba(111, 43, 31, 0.16);
}

.replace-button:disabled {
  cursor: default;
  opacity: 0.48;
}

.script-scroll {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow: hidden;
  padding: 3px 4px;
}

.script-theme-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(118px, 0.82fr) minmax(0, 2.18fr);
  align-items: center;
  gap: 14px;
  flex: 1 1 0;
  min-height: 0;
  padding: 10px 13px 10px 15px;
  overflow: hidden;
  border: 1px solid rgba(92, 61, 38, 0.18);
  border-radius: 13px;
  background:
    linear-gradient(135deg, rgba(255, 252, 242, 0.96), rgba(246, 232, 205, 0.88)),
    #f8ecd8;
  box-shadow:
    0 8px 18px rgba(70, 40, 22, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.script-theme-card::before {
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 0;
  width: 4px;
  border-radius: 0 999px 999px 0;
  background: linear-gradient(180deg, #b64234, #7f2f28);
  content: "";
}

.script-theme-card::after {
  position: absolute;
  top: 9px;
  right: 11px;
  width: 30px;
  height: 15px;
  border-top: 1px solid rgba(92, 61, 38, 0.22);
  border-right: 1px solid rgba(92, 61, 38, 0.22);
  border-radius: 0 8px 0 0;
  opacity: 0.9;
  content: "";
}

.script-name-block {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding-right: 13px;
  text-align: center;
  border-right: 1px solid rgba(92, 61, 38, 0.15);
}

.script-name-block strong {
  display: block;
  overflow: hidden;
  color: #261914;
  font-size: 23px;
  font-weight: 1000;
  line-height: 1.08;
  letter-spacing: 0.03em;
  text-shadow: 0 1px 0 rgba(255, 249, 234, 0.9);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-name-block span {
  display: inline-grid;
  max-width: 100%;
  height: 23px;
  margin-top: 9px;
  padding: 0 10px;
  overflow: hidden;
  place-items: center;
  border: 1px solid rgba(114, 33, 27, 0.36);
  border-radius: 5px;
  color: #fff7e7;
  font-size: 12px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: 0.08em;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  background:
    linear-gradient(180deg, rgba(190, 72, 58, 0.98), rgba(136, 46, 38, 0.98)),
    #a63b31;
  box-shadow:
    inset 0 0 0 1px rgba(255, 232, 203, 0.22),
    0 3px 8px rgba(128, 49, 37, 0.16);
}

.theme-bars {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  height: 76px;
  min-width: 0;
}

.theme-state {
  display: grid;
  flex: 1;
  min-height: 0;
  place-items: center;
  color: #6b4628;
  font-size: 15px;
  font-weight: 900;
}

.theme-state--error {
  color: #8f2f24;
}
</style>
