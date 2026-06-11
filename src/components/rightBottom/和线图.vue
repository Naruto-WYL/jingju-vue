<template>
  <div class="play-chord-shell">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>
    <div v-else-if="error" class="theme-state theme-state--error">{{ error }}</div>

    <div v-else class="play-chord-panel">
      <article
        v-for="(item, index) in displaySlots"
        :key="item.playId || index"
        class="play-chord-card"
      >
        <div :ref="(el) => setChartRef(el, index)" class="g2-play-chord" />

        <label class="play-picker">
          <select v-model="selectedPlayIds[index]">
            <option
              v-for="play in playOptions"
              :key="play.playId"
              :value="play.playId"
            >
              {{ play.title }}
            </option>
          </select>
        </label>
      </article>
    </div>
  </div>
</template>

<script setup>
import { Chart } from '@antv/g2'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const THEME_CSV_URL = `${import.meta.env.BASE_URL}数据表合集/3/theme_analysis.csv`
const KAI_FONT = '"STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif'
const PLAY_COUNT = 4

const rows = ref([])
const loading = ref(true)
const error = ref('')

const selectedPlayIds = ref([])
const chartRefs = ref([])
const chartInstances = []

const themeColors = {
  家庭伦理: '#ad3936',
  婚恋情感: '#ae688a',
  身份变换: '#4f7da8',
  公案审判: '#26776f',
  复仇伸冤: '#8b2a25',
  忠义家国: '#cd9744',
  战争冲突: '#6d597a',
  权力斗争: '#7f5539',
  英雄悲情: '#d35f50',
  忠义抉择: '#4f7da8',
  家国冲突: '#7f5539',
  爱情牺牲: '#c06a96',
  命运转折: '#b9823d',
  家庭冲突: '#ad3936',
  女性冤情: '#ae688a',
  伦理秩序: '#8b2a25',
  亲情选择: '#cd9744',
  谋略联盟: '#5b8ff9',
  战争策略: '#6d597a',
  盟友试探: '#2f8b7d',
  真假识别: '#d8a146',
  人情交易: '#9c6a4e',
  才子遭嫉: '#8a6ab0',
  忠直殉志: '#bf7b48',
  人蛇情缘: '#7d6ab4',
  反抗礼法: '#c26c78',
  水漫金山: '#5d95c8',
  神佛干预: '#6d5bd0',
  未识别主题: '#b9a98c',
}

const fallbackThemeColors = [
  '#5B8FF9',
  '#5AD8A6',
  '#F6BD16',
  '#E86452',
  '#6D5BD0',
  '#FF99C3',
]

const genreColors = {
  传统: '#d6aa55',
  公案: '#2f8b7d',
  神怪: '#7d6ab4',
  三国: '#cf6a4c',
  水浒: '#5d95c8',
  战争: '#b9823d',
  爱情: '#c06a96',
  宫廷: '#9c6a4e',
  汉代: '#bf7b48',
  宋代: '#7f9f64',
  明代: '#8a6ab0',
  秦代: '#c26c78',
  楚汉悲歌: '#e86452',
  公案伦理: '#2f8b7d',
  三国谋略: '#5b8ff9',
  婚恋公案: '#c06a96',
  神话爱情: '#7d6ab4',
  家国亲情: '#d8a146',
  武戏冲突: '#6d597a',
  宫廷情感: '#9c6a4e',
  生活喜剧: '#5ad8a6',
}

const plays = computed(() => groupRowsByPlay(rows.value))

const playMap = computed(() => new Map(plays.value.map((play) => [play.playId, play])))

const playOptions = computed(() =>
  plays.value
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a)),
)

const displaySlots = computed(() =>
  selectedPlayIds.value.slice(0, PLAY_COUNT).map((playId) => ({
    playId,
    play: playMap.value.get(playId),
  })),
)

onMounted(async () => {
  await loadThemeCsv()
})

watch(
  plays,
  () => {
    reconcileSelectedPlays()
  },
  { immediate: true },
)

watch(
  displaySlots,
  async () => {
    await renderCharts()
  },
  { deep: true, flush: 'post' },
)

onBeforeUnmount(() => {
  destroyCharts()
})

async function loadThemeCsv() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(`${THEME_CSV_URL}?t=${Date.now()}`, {
      cache: 'no-store',
    })

    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`)
    }

    const text = await response.text()
    rows.value = parseThemeCsv(text)
  } catch (err) {
    error.value = `主题CSV读取失败：${err.message}`
    rows.value = []
  } finally {
    loading.value = false
  }
}

function setChartRef(el, index) {
  if (el) {
    chartRefs.value[index] = el
  }
}

function reconcileSelectedPlays() {
  if (!plays.value.length) {
    selectedPlayIds.value = []
    return
  }

  const validIds = new Set(plays.value.map((play) => play.playId))

  const nextIds = selectedPlayIds.value
    .filter((id) => validIds.has(id))
    .slice(0, PLAY_COUNT)

  const usedIds = new Set(nextIds)
  const defaults = pickRepresentativePlays(plays.value, PLAY_COUNT)

  defaults.forEach((play) => {
    if (nextIds.length >= PLAY_COUNT) return
    if (usedIds.has(play.playId)) return

    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  playOptions.value.forEach((play) => {
    if (nextIds.length >= PLAY_COUNT) return
    if (usedIds.has(play.playId)) return

    nextIds.push(play.playId)
    usedIds.add(play.playId)
  })

  selectedPlayIds.value = nextIds
  chartRefs.value = chartRefs.value.slice(0, PLAY_COUNT)
}

async function renderCharts() {
  await nextTick()

  destroyCharts()

  displaySlots.value.forEach((item, index) => {
    const container = chartRefs.value[index]
    const play = item.play
    const links = play ? buildPlayLinks(play) : []

    if (!container || !play || !links.length) return

    const chart = new Chart({
      container,
      theme: 'classic',
      autoFit: true,
    })

    chart.options({
      type: 'chord',
      autoFit: true,
      data: {
        value: {
          links,
        },
      },
      layout: {
        nodeWidthRatio: 0.055,
      },
      scale: {
        color: {
          type: 'ordinal',
          range: colorRangeForPlay(play),
        },
      },
      style: {
  labelFontFamily: KAI_FONT,
  labelFontSize: 9,
  labelFill: '#4f3a2b',
  labelFontWeight: 700,

  nodeStroke: 'rgba(255, 248, 235, 0.88)',
  nodeLineWidth: 0.8,

  linkFill: genreColor(play.genre),
  linkFillOpacity: 0.48,
  linkStroke: genreColor(play.genre),
  linkStrokeOpacity: 0.18,
},
      tooltip: {
        items: [
          { field: 'playTitle', name: '剧本' },
          { field: 'genre', name: '剧目类型' },
          { field: 'source', name: '主题A' },
          { field: 'target', name: '主题B' },
          { field: 'value', name: '共现强度' },
        ],
      },
      interaction: [
        {
          type: 'elementHighlight',
          background: true,
        },
      ],
    })

    chart.render()
    chartInstances.push(chart)
  })
}

function destroyCharts() {
  while (chartInstances.length) {
    const chart = chartInstances.pop()

    chart.destroy()
  }
}

function pickRepresentativePlays(sourcePlays, limit) {
  const buckets = new Map()

  sourcePlays.forEach((play) => {
    const count = play.themes.length

    if (!buckets.has(count)) {
      buckets.set(count, [])
    }

    buckets.get(count).push(play)
  })

  const selected = []
  const selectedIds = new Set()
  const counts = Array.from(buckets.keys()).sort((a, b) => a - b)

  counts.forEach((count) => {
    const candidates = buckets
      .get(count)
      .slice()
      .sort((a, b) => dominantShare(b) - dominantShare(a))

    candidates.slice(0, 2).forEach((play) => {
      if (selected.length >= limit) return
      if (selectedIds.has(play.playId)) return

      selected.push(play)
      selectedIds.add(play.playId)
    })
  })

  sourcePlays
    .slice()
    .sort((a, b) => b.themes.length - a.themes.length || dominantShare(b) - dominantShare(a))
    .forEach((play) => {
      if (selected.length >= limit) return
      if (selectedIds.has(play.playId)) return

      selected.push(play)
      selectedIds.add(play.playId)
    })

  return selected
}

function buildPlayLinks(play) {
  const themes = normalizedThemes(play)
  const links = []

  for (let left = 0; left < themes.length; left += 1) {
    for (let right = left + 1; right < themes.length; right += 1) {
      const strength = Math.sqrt(themes[left].share * themes[right].share)
      const value = Number((strength * 100).toFixed(2))

      links.push({
        source: themes[left].name,
        target: themes[right].name,
        value,
        genre: play.genre,
        playTitle: play.title,
      })

      links.push({
        source: themes[right].name,
        target: themes[left].name,
        value: Number((value * 0.72).toFixed(2)),
        genre: play.genre,
        playTitle: play.title,
      })
    }
  }

  if (themes.length === 1) {
    links.push({
      source: themes[0].name,
      target: themes[0].name,
      value: Number((themes[0].share * 100).toFixed(2)),
      genre: play.genre,
      playTitle: play.title,
    })
  }

  return links
}

function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)
  const total = validThemes.reduce((sum, theme) => sum + Number(theme.share || 0), 0) || 1

  return validThemes.map((theme) => ({
    ...theme,
    share: Number(theme.share || 0) / total,
  }))
}

function colorRangeForPlay(play) {
  return normalizedThemes(play).map((theme) => themeColor(theme.name))
}

function dominantShare(play) {
  return Math.max(0, ...play.themes.map((theme) => Number(theme.share || 0)))
}

function themeColor(name) {
  if (themeColors[name]) return themeColors[name]

  const code = Array.from(String(name)).reduce((sum, char) => sum + char.charCodeAt(0), 0)

  return fallbackThemeColors[code % fallbackThemeColors.length]
}

function genreColor(genre) {
  return genreColors[genre] || '#d6aa55'
}

function parseThemeCsv(text) {
  const cleanText = String(text || '').trim()

  if (!cleanText) return []

  const [headerLine, ...lines] = cleanText.split(/\r?\n/)
  const headers = splitCsvLine(headerLine).map((header) => header.trim())

  return lines
    .filter((line) => line.trim())
    .map((line) => {
      const values = splitCsvLine(line)
      const row = Object.fromEntries(headers.map((header, index) => [header, values[index] || '']))

      return {
        play_id: String(row.play_id || '').trim(),
        title: String(row.title || '').trim(),
        genre: String(row.genre || '').trim(),
        collection: String(row.collection || '').trim(),
        theme: String(row.theme || '').trim(),
        score: toNumber(row.score),
        share: toShare(row.share),
        rank: toNumber(row.rank),
      }
    })
    .filter((row) => row.play_id && row.title && row.theme)
}

function splitCsvLine(line) {
  const cells = []
  let cell = ''
  let quoted = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]

    if (char === '"' && quoted && next === '"') {
      cell += '"'
      index += 1
    } else if (char === '"') {
      quoted = !quoted
    } else if (char === ',' && !quoted) {
      cells.push(cell)
      cell = ''
    } else {
      cell += char
    }
  }

  cells.push(cell)

  return cells
}

function groupRowsByPlay(sourceRows) {
  const map = new Map()

  sourceRows.forEach((row) => {
    if (!map.has(row.play_id)) {
      map.set(row.play_id, {
        playId: row.play_id,
        title: row.title,
        genre: row.genre,
        collection: row.collection,
        themes: [],
      })
    }

    map.get(row.play_id).themes.push({
      name: row.theme,
      score: row.score,
      share: row.share,
      rank: row.rank,
    })
  })

  return Array.from(map.values()).map((play) => ({
    ...play,
    themes: play.themes
      .slice()
      .sort((a, b) => {
        const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
        const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999

        return rankA - rankB || b.share - a.share
      }),
  }))
}

function toNumber(value) {
  const number = Number(String(value ?? '').replace('%', '').trim())

  return Number.isFinite(number) ? number : 0
}

function toShare(value) {
  const raw = String(value ?? '').trim()

  if (!raw) return 0

  const hasPercent = raw.includes('%')
  const number = Number(raw.replace('%', '').trim())

  if (!Number.isFinite(number)) return 0

  if (hasPercent) return number / 100

  return number > 1 ? number / 100 : number
}
</script>

<style scoped>
.play-chord-shell {
  width: 100%;
  height: 100%;
  min-height: 0;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
}

.play-chord-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.play-chord-card {
  display: grid;
  grid-template-rows: minmax(0, 1fr) 28px;
  gap: 2px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.g2-play-chord {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.play-picker {
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 0 12px 4px;
}

.play-picker select {
  width: 72%;
  height: 24px;
  min-width: 0;
  padding: 0 22px 0 9px;

  border: 1px solid rgba(139, 91, 52, 0.24);
  border-radius: 999px;
  outline: none;

  color: #5a3928;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 12px;
  font-weight: 900;

  background:
    linear-gradient(180deg, rgba(255, 250, 238, 0.92), rgba(246, 236, 214, 0.78)),
    #f6ecd6;

  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.5),
    0 2px 5px rgba(80, 43, 25, 0.06);

  cursor: pointer;
}

.play-picker select:hover {
  border-color: rgba(143, 47, 36, 0.34);
  color: #8f2f24;
}

.play-picker select:focus {
  border-color: rgba(184, 147, 73, 0.62);
  box-shadow:
    0 0 0 2px rgba(184, 147, 73, 0.14),
    inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.theme-state {
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  place-items: center;
  color: #6b4628;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 15px;
  font-weight: 900;
}

.theme-state--error {
  color: #8f2f24;
}
</style>