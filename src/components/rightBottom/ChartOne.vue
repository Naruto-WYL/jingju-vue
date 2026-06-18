<template>
  <div class="play-chord-shell">
    <div v-if="loading" class="theme-state">主题数据加载中...</div>
    <div v-else-if="error" class="theme-state theme-state--error">{{ error }}</div>

    <div v-else class="play-chord-panel" :class="{ 'is-focused': focusedPlayId }">
      <article
        v-for="(item, index) in displaySlots"
        :key="item.playId || index"
        class="play-chord-card"
        :class="{ 'is-focus-card': focusedPlayId && index === 0 }"
      >
        <div v-if="focusedPlayId && index === 0 && item.play" class="focus-summary">
          <strong>{{ item.play.title }}</strong>
          <span>{{ focusLabel(item.play) }}</span>
        </div>

        <div class="play-visual-zone" :class="{ 'has-theme-dashboard': focusedPlayId && index === 0 }">
          <div :ref="(el) => setChartRef(el, index)" class="g2-play-chord" />

          <aside v-if="focusedPlayId && index === 0 && item.play" class="theme-dashboard">
            <div class="focus-meta-line">
              <span>角色：{{ focusedCharacterCount(item.play) }}人</span>
              <span>场次：{{ focusedSceneLabel(item.play) }}</span>
              <span>主题：{{ normalizedThemes(item.play).length }}类</span>
            </div>

            <div class="theme-stack" aria-hidden="true">
              <i
                v-for="theme in themeSummary(item.play)"
                :key="theme.themeId"
                :style="{
                  flexGrow: Math.max(theme.share, 0.025),
                  background: themeColor(theme.name),
                  opacity: isFocusedTheme(theme.themeId) ? 1 : 0.55,
                }"
              ></i>
            </div>

            <div class="theme-rank-list">
              <div
                v-for="theme in themeSummary(item.play)"
                :key="theme.themeId"
                class="theme-rank-row"
                :class="{ active: isFocusedTheme(theme.themeId) }"
              >
                <span class="theme-dot" :style="{ background: themeColor(theme.name) }"></span>
                <b>{{ theme.name }}</b>
                <i><em :style="{ width: `${Math.max(3, Math.round(theme.share * 100))}%`, background: themeColor(theme.name) }"></em></i>
                <strong>{{ formatPercent(theme.share) }}</strong>
              </div>
            </div>

            <p class="focus-scene-text">{{ focusedSceneText(item.play) }}</p>
          </aside>
        </div>

        <button
          v-if="focusedPlayId && index === 0"
          class="play-focus-close"
          type="button"
          aria-label="关闭联动主题图"
          @click="clearFocusedPlay"
        >
          ×
        </button>

        <label v-if="!focusedPlayId" class="play-picker">
          <select :value="item.playId" :disabled="Boolean(focusedPlayId)" @change="handlePlayPickerChange(index, $event)">
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
import { clearLinkageFocus, linkageState, loadLinkageData } from '../../services/linkageStore'

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

const focusedPlayId = computed(() => {
  if (!isLinkageTriggerSource()) return ''
  return playMap.value.has(linkageState.selectedPlayId) ? linkageState.selectedPlayId : ''
})

const displaySlots = computed(() => {
  if (focusedPlayId.value) {
    return [
      {
        playId: focusedPlayId.value,
        play: playMap.value.get(focusedPlayId.value),
      },
    ]
  }

  return selectedPlayIds.value.slice(0, PLAY_COUNT).map((playId) => ({
    playId,
    play: playMap.value.get(playId),
  }))
})

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

watch(
  () => linkageState.selectedThemeIds.slice(),
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
    const linkageData = await loadLinkageData()
    if (linkageData.plays?.length) {
      rows.value = linkageData.plays.flatMap((play) => (play.themes || []).map((theme) => normalizeLinkageTheme(play, theme)))
      return
    }

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

function normalizeLinkageTheme(play, theme) {
  return {
    play_id: play.play_id,
    title: play.title,
    genre: play.themes?.[0]?.theme || '传统',
    collection: '五剧本联动',
    theme_id: theme.theme_id,
    theme: theme.theme,
    score: Number(theme.score) || 0,
    share: Number(theme.share) || 0,
    rank: Number(theme.rank) || 0,
  }
}

function setChartRef(el, index) {
  if (el) {
    chartRefs.value[index] = el
  }
}

function handlePlayPickerChange(index, event) {
  const playId = event.target?.value || ''
  if (!playId) return

  selectedPlayIds.value[index] = playId
}

function clearFocusedPlay() {
  clearLinkageFocus('rightBottomClear')
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
    const hasThemeFocus = isLinkageTriggerSource() && linkageState.selectedThemeIds.length > 0

    if (!container || !play || !links.length) return

    const chartSizing = getChordChartSizing(container, Boolean(focusedPlayId.value && index === 0))

    const chart = new Chart({
      container,
      theme: 'classic',
      autoFit: true,
    })

    chart.options({
      type: 'chord',
      autoFit: true,
      paddingTop: chartSizing.paddingTop,
      paddingRight: chartSizing.paddingX,
      paddingBottom: chartSizing.paddingBottom,
      paddingLeft: chartSizing.paddingX,
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
        labelFontSize: chartSizing.labelFontSize,
        labelFill: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? '#8b1f1b' : '#4f3a2b'),
        labelFontWeight: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? 1000 : 800),

        nodeStroke: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? '#8b1f1b' : 'rgba(255, 248, 235, 0.88)'),
        nodeLineWidth: (datum) => (hasThemeFocus && isFocusedChordDatum(datum, play) ? 2.4 : 0.8),
        nodeFillOpacity: (datum) => (hasThemeFocus ? (isFocusedChordDatum(datum, play) ? 1 : 0.32) : 0.95),

        linkFill: (datum) => (hasThemeFocus && datum.isFocus ? '#b23b32' : genreColor(play.genre)),
        linkFillOpacity: (datum) => (hasThemeFocus ? (datum.isFocus ? 0.82 : 0.1) : 0.48),
        linkStroke: (datum) => (hasThemeFocus && datum.isFocus ? '#7a1f1b' : genreColor(play.genre)),
        linkStrokeOpacity: (datum) => (hasThemeFocus ? (datum.isFocus ? 0.68 : 0.05) : 0.18),
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

function getChordChartSizing(container, isFocused = false) {
  const rect = container.getBoundingClientRect()
  const minSide = Math.min(rect.width || 0, rect.height || 0)

  if (isFocused) {
    return {
      labelFontSize: minSide < 180 ? 11 : 12.5,
      paddingX: 0,
      paddingTop: 0,
      paddingBottom: 0,
    }
  }

  if (minSide < 120) {
    return {
      labelFontSize: 10.5,
      paddingX: 14,
      paddingTop: 10,
      paddingBottom: 8,
    }
  }

  if (minSide < 170) {
    return {
      labelFontSize: 11,
      paddingX: 16,
      paddingTop: 12,
      paddingBottom: 9,
    }
  }

  return {
    labelFontSize: 12,
    paddingX: 22,
    paddingTop: 16,
    paddingBottom: 11,
  }
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
        sourceThemeId: themes[left].themeId,
        targetThemeId: themes[right].themeId,
        isFocus: isFocusedTheme(themes[left].themeId) || isFocusedTheme(themes[right].themeId),
        value,
        genre: play.genre,
        playTitle: play.title,
      })

      links.push({
        source: themes[right].name,
        target: themes[left].name,
        sourceThemeId: themes[right].themeId,
        targetThemeId: themes[left].themeId,
        isFocus: isFocusedTheme(themes[right].themeId) || isFocusedTheme(themes[left].themeId),
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
      sourceThemeId: themes[0].themeId,
      targetThemeId: themes[0].themeId,
      isFocus: isFocusedTheme(themes[0].themeId),
      value: Number((themes[0].share * 100).toFixed(2)),
      genre: play.genre,
      playTitle: play.title,
    })
  }

  return links
}

function isFocusedTheme(themeId) {
  return isLinkageTriggerSource() && linkageState.selectedThemeIds.includes(themeId)
}

function isFocusedChordDatum(datum, play) {
  if (!isLinkageTriggerSource() || !linkageState.selectedThemeIds.length) return false
  if (datum?.isFocus) return true

  const focusIds = new Set(linkageState.selectedThemeIds)
  const focusNames = new Set(
    normalizedThemes(play)
      .filter((theme) => focusIds.has(theme.themeId))
      .map((theme) => theme.name),
  )
  const values = new Set()
  collectThemeDatumValues(datum, values)

  return Array.from(values).some((value) => focusIds.has(value) || focusNames.has(value))
}

function collectThemeDatumValues(value, values) {
  if (value === null || value === undefined) return

  if (typeof value !== 'object') {
    values.add(text(value))
    return
  }

  ;['themeId', 'sourceThemeId', 'targetThemeId', 'id', 'key', 'name', 'theme', 'source', 'target'].forEach((key) => {
    if (value[key] !== undefined) values.add(text(value[key]))
  })

  if (value.data && value.data !== value) {
    collectThemeDatumValues(value.data, values)
  }
}

function text(value) {
  return String(value ?? '').trim()
}

function isLinkageTriggerSource() {
  return linkageState.source === 'leftTopIcon' || linkageState.source === 'rightTopNode'
}

function focusLabel(play) {
  if (linkageState.selectedTrade) return `${linkageState.selectedTrade}行当联动`
  const character = linkagePlay(play)?.characters?.find((item) => item.character_id === linkageState.selectedCharacterId)
  if (character?.name) return `${character.name}角色联动`
  return '主题联动视图'
}

function focusedCharacterCount(play) {
  const fullPlay = linkagePlay(play)
  if (!fullPlay) return 0
  const trade = normalizeTrade(linkageState.selectedTrade)
  if (!trade) return linkageState.selectedCharacterId ? 1 : fullPlay.characters?.length || 0
  return (
    fullPlay.characters?.filter((character) => {
      return (
        normalizeTrade(character.standard_trade || character.trade) === trade ||
        normalizeTrade(character.major_trade) === trade
      )
    }).length || 0
  )
}

function focusedSceneLabel(play) {
  const scene = focusedScene(play)
  return scene?.scene_label || scene?.stage_type || '-'
}

function focusedSceneText(play) {
  const scene = focusedScene(play)
  if (!scene) return '当前联动暂未匹配到具体场次。'
  const stage = scene.stage_type ? `${scene.stage_type} · ` : ''
  const summary = scene.summary || '暂无场景摘要'
  return `${stage}${summary}`
}

function focusedScene(play) {
  const fullPlay = linkagePlay(play)
  return fullPlay?.scenes?.find((scene) => scene.scene_id === linkageState.selectedSceneId) || null
}

function linkagePlay(play) {
  return linkageState.plays.find((item) => item.play_id === play?.playId) || null
}

function themeSummary(play) {
  return normalizedThemes(play)
    .slice()
    .sort((a, b) => {
      const rankA = Number.isFinite(a.rank) && a.rank > 0 ? a.rank : 999
      const rankB = Number.isFinite(b.rank) && b.rank > 0 ? b.rank : 999
      return b.share - a.share || rankA - rankB
    })
    .slice(0, 6)
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`
}

function normalizeTrade(value) {
  return text(value).replace(/[（(].*?[）)]/g, '')
}

function normalizedThemes(play) {
  const validThemes = play.themes.filter((theme) => theme.name)
  const total = validThemes.reduce((sum, theme) => sum + Number(theme.share || 0), 0) || 1

  return validThemes.map((theme) => ({
    ...theme,
    themeId: text(theme.themeId || theme.theme_id || theme.id || theme.name),
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
        theme_id: String(row.theme_id || '').trim(),
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
      themeId: row.theme_id,
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
  background: #FBF6E9;
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
  background: #FBF6E9;
}

.play-chord-card {
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 24px;
  gap: 2px;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: none;
  border-radius: 0;
  background: #FBF6E9;
  box-shadow: none;
}

.play-chord-card.is-focus-card {
  display: grid;
  grid-template-rows: 20px minmax(0, 1fr);
  gap: 0;
}

.focus-summary {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  padding: 1px 34px 0 4px;
  color: #4b3328;
  line-height: 1.15;
}

.is-focus-card .focus-summary {
  position: relative;
  top: auto;
  right: auto;
  left: auto;
  z-index: 3;
  padding: 0 34px 0 4px;
  pointer-events: none;
}

.focus-summary strong {
  overflow: hidden;
  color: #8f2f24;
  font-size: 16px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.focus-summary span {
  flex: 0 0 auto;
  color: #806a58;
  font-family: "Microsoft YaHei", sans-serif;
  font-size: 11px;
  font-weight: 800;
}

.play-visual-zone {
  min-width: 0;
  min-height: 0;
}

.play-visual-zone.has-theme-dashboard {
  position: relative;
  inset: auto;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  height: auto;
  padding: 0;
}

.play-focus-close {
  position: absolute;
  top: 6px;
  right: 8px;
  z-index: 2;
  width: 24px;
  height: 24px;
  border: 1px solid rgba(139, 42, 37, 0.3);
  border-radius: 50%;
  background: rgba(255, 252, 244, 0.9);
  color: #8b2a25;
  font-size: 16px;
  font-weight: 900;
  line-height: 20px;
  cursor: pointer;
}

.play-chord-panel.is-focused {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
}

.g2-play-chord {
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: visible;
}

.play-chord-panel.is-focused .g2-play-chord {
  position: relative;
  inset: auto;
  min-width: 0;
  min-height: 0;
}

.theme-dashboard {
  position: relative;
  top: auto;
  right: auto;
  bottom: auto;
  z-index: 2;
  display: grid;
  grid-template-columns: minmax(82px, 0.8fr) minmax(110px, 1fr) minmax(150px, 1.45fr) minmax(90px, 1fr);
  align-items: center;
  gap: 5px;
  width: auto;
  min-width: 0;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 4px 1px;
  color: #4b3328;
  font-family: "Microsoft YaHei", sans-serif;
  background: rgba(251, 246, 233, 0.96);
  border-top: 1px solid rgba(143, 47, 36, 0.1);
  scrollbar-color: rgba(143, 47, 36, 0.32) #FBF6E9;
  scrollbar-width: thin;
}

.theme-dashboard::-webkit-scrollbar {
  height: 6px;
}

.theme-dashboard::-webkit-scrollbar-track {
  background: #FBF6E9;
}

.theme-dashboard::-webkit-scrollbar-thumb {
  background: rgba(143, 47, 36, 0.3);
  border: 2px solid #FBF6E9;
  border-radius: 999px;
}

.focus-meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 6px;
  margin-bottom: 0;
  color: #806a58;
  font-size: 11px;
  font-weight: 800;
  line-height: 1.2;
}

.theme-stack {
  display: flex;
  width: 100%;
  height: 12px;
  min-height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(143, 47, 36, 0.08);
}

.theme-stack i {
  min-width: 4px;
  height: 100%;
}

.theme-rank-list {
  display: flex;
  gap: 4px;
  margin-top: 0;
  min-width: 0;
  overflow: hidden;
}

.theme-rank-row {
  display: grid;
  grid-template-columns: 8px minmax(36px, 1fr) 30px;
  align-items: center;
  gap: 4px;
  flex: 1 1 0;
  min-width: 0;
  opacity: 0.62;
}

.theme-rank-row.active,
.theme-rank-row:first-child {
  opacity: 1;
}

.theme-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.theme-rank-row b {
  overflow: hidden;
  color: #4b3328;
  font-size: 10.5px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-rank-row i {
  display: none;
}

.theme-rank-row em {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.theme-rank-row strong {
  color: #8f2f24;
  font-size: 10.5px;
  font-weight: 900;
  text-align: right;
}

.focus-scene-text {
  flex: initial;
  min-height: 0;
  margin: 0;
  overflow: hidden;
  color: #5c4636;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 1.38;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  scrollbar-color: rgba(143, 47, 36, 0.34) #FBF6E9;
  scrollbar-width: thin;
}

.focus-scene-text::-webkit-scrollbar {
  width: 6px;
}

.focus-scene-text::-webkit-scrollbar-track {
  background: #FBF6E9;
}

.focus-scene-text::-webkit-scrollbar-thumb {
  background: rgba(143, 47, 36, 0.32);
  border: 2px solid #FBF6E9;
  border-radius: 999px;
}

.play-picker {
  display: flex;
  justify-content: center;
  min-width: 0;
  padding: 0 10px 2px;
}

.play-picker select {
  width: 72%;
  height: 22px;
  min-width: 0;
  padding: 0 22px 0 9px;

  border: 1px solid rgba(139, 91, 52, 0.24);
  border-radius: 999px;
  outline: none;

  color: #5a3928;
  font-family: "STKaiti", "KaiTi", "FangSong", "Microsoft YaHei", serif;
  font-size: 13px;
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
