<template>
  <section class="theme-card-view" aria-label="剧本主题构成">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>
    <div v-else-if="error" class="theme-state theme-state--error">{{ error }}</div>

    <div v-else class="script-scroll">
      <article v-for="(play, index) in visiblePlays" :key="play.playId" class="script-theme-card">
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

let resizeObserver = null

const themePalette = ['#d79021', '#df3f37', '#7e5198', '#21877b', '#4f7fa7']

const plays = computed(() =>
  groupRowsByPlay(rows.value).filter((play) => play.playId && play.title && play.themes.length),
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
  },
  { deep: true, flush: 'post' },
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => renderThemeBars())
  observeCharts()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

function setChartRef(el, index) {
  if (el) chartRefs.value[index] = el
}

function observeCharts() {
  if (!resizeObserver) return
  resizeObserver.disconnect()
  chartRefs.value.forEach((element) => {
    if (element) resizeObserver.observe(element)
  })
}

function reconcileDisplayedPlays() {
  if (!plays.value.length) return

  const validIds = new Set(plays.value.map((play) => play.playId))
  const nextIds = displayedPlayIds.value.filter((playId) => validIds.has(playId)).slice(0, CARD_COUNT)
  const usedIds = new Set(nextIds)

  playOptions.value.forEach((play) => {
    if (nextIds.length >= CARD_COUNT || usedIds.has(play.playId)) return
    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  displayedPlayIds.value = nextIds
  chartRefs.value = chartRefs.value.slice(0, CARD_COUNT)
}

function renderThemeBars() {
  visiblePlays.value.forEach((play, index) => {
    drawThemeBars(chartRefs.value[index], play)
  })
}

function drawThemeBars(svgElement, play) {
  if (!svgElement) return

  const themes = normalizedThemes(play).slice(0, 5)
  const width = Math.max(230, Math.round(svgElement.clientWidth || 300))
  const height = 64
  const columns = 2
  const columnGap = 12
  const rowGap = 20
  const itemWidth = (width - columnGap) / columns
  const percentWidth = 24
  const barWidth = Math.max(45, itemWidth - percentWidth - 4)
  const maxShare = Math.max(0.01, d3.max(themes, (theme) => theme.share) || 0)

  const svg = d3.select(svgElement)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${width} ${height}`)
  svg.attr('preserveAspectRatio', 'none')

  const rows = svg
    .selectAll('g.theme-row')
    .data(themes)
    .join('g')
    .attr('class', 'theme-row')
    .attr('transform', (_, index) => {
      const column = index % columns
      const row = Math.floor(index / columns)
      return `translate(${column * (itemWidth + columnGap)},${6 + row * rowGap})`
    })

  rows
    .append('text')
    .attr('x', 0)
    .attr('y', 0)
    .attr('dy', '0.8em')
    .attr('text-anchor', 'start')
    .attr('fill', (theme, index) => themePalette[index % themePalette.length])
    .attr('font-family', KAI_FONT)
    .attr('font-size', 11)
    .attr('font-weight', 900)
    .text((theme) => themeLabel(theme.name))

  rows
    .append('line')
    .attr('x1', 0)
    .attr('x2', barWidth)
    .attr('y1', 16)
    .attr('y2', 16)
    .attr('stroke', 'rgba(117, 76, 38, 0.14)')
    .attr('stroke-width', 3.4)
    .attr('stroke-linecap', 'round')

  rows
    .append('line')
    .attr('x1', 0)
    .attr('x2', (theme) => (theme.share / maxShare) * barWidth)
    .attr('y1', 16)
    .attr('y2', 16)
    .attr('stroke', (theme, index) => themePalette[index % themePalette.length])
    .attr('stroke-width', 4.2)
    .attr('stroke-linecap', 'round')

  rows
    .append('text')
    .attr('x', itemWidth)
    .attr('y', 16)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('fill', '#3a2016')
    .attr('font-family', KAI_FONT)
    .attr('font-size', 10)
    .attr('font-weight', 900)
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
</script>

<style scoped>
.theme-card-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  color: #442519;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.script-scroll {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: hidden;
  padding: 2px 3px 3px 1px;
}

.script-theme-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(112px, 0.78fr) minmax(0, 2.06fr);
  align-items: center;
  gap: 12px;
  flex: 1 1 0;
  min-height: 0;
  padding: 8px 11px 8px 13px;
  overflow: hidden;
  border: 0;
  border-radius: 12px;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.82), rgba(255, 248, 231, 0.72)),
    linear-gradient(180deg, rgba(255, 253, 244, 0.95), rgba(245, 229, 199, 0.84)),
    #fff4dd;
  box-shadow:
    0 9px 18px rgba(85, 45, 18, 0.14),
    0 2px 5px rgba(85, 45, 18, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.script-name-block {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding-left: 1px;
  text-align: center;
}

.script-name-block strong {
  display: block;
  overflow: hidden;
  color: #241811;
  font-size: 25px;
  font-weight: 1000;
  line-height: 1.1;
  text-shadow: 0 1px 0 rgba(255, 251, 238, 0.86);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.script-name-block span {
  display: inline-grid;
  max-width: 100%;
  height: 22px;
  margin-top: 9px;
  padding: 0 11px;
  overflow: hidden;
  place-items: center;
  border: 1px solid rgba(210, 166, 98, 0.58);
  border-radius: 999px;
  color: #7a4b1f;
  font-size: 13px;
  font-weight: 900;
  line-height: 1;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
  background:
    linear-gradient(180deg, rgba(255, 252, 239, 0.96), rgba(247, 226, 184, 0.78)),
    #fff4dd;
  box-shadow: inset 0 0 0 1px rgba(255, 250, 234, 0.74);
}

.theme-bars {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  padding-left: 12px;
  border-left: 1px solid rgba(205, 160, 91, 0.22);
}

.theme-state {
  display: grid;
  flex: 1;
  min-height: 0;
  place-items: center;
  color: #6a4526;
  font-size: 15px;
  font-weight: 900;
}

.theme-state--error {
  color: #8f2f24;
}
</style>
